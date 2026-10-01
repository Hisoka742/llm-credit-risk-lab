"""GigaChat as a backend for the same extraction code path (`extract_one`).

GigaChat's chat endpoint is OpenAI-compatible, but authentication is not: a long-lived
*authorization key* is exchanged for an access token that expires after about 30 minutes.
This module hides that behind an ordinary `openai.OpenAI` client, so schema validation,
retries and the disk cache in `src.features.llm_extract` are reused unchanged.

Secrets come from the environment only (`.env`, never the config or the repo):
    GIGACHAT_AUTH_KEY    authorization key from the GigaChat API project page
    GIGACHAT_CA_BUNDLE   optional path to a PEM file with the Russian Trusted Root CA.
                         Sber's endpoints use a certificate chain that is not in the default
                         trust store, so without it TLS verification fails.
    GIGACHAT_VERIFY_SSL  "false" turns verification off. For a quick local test only: it
                         removes the protection against a man-in-the-middle.
"""

from __future__ import annotations

import os
import ssl
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from src.features.llm_extract import FatalLLMError

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
BASE_URL = "https://gigachat.devices.sberbank.ru/api/v1"
# Refresh this long before expiry, so a request never leaves with a token about to lapse.
REFRESH_MARGIN_S = 60.0


@dataclass(frozen=True)
class GigaChatConfig:
    auth_url: str = AUTH_URL
    base_url: str = BASE_URL
    scope: str = "GIGACHAT_API_PERS"  # _PERS individuals, _B2B / _CORP for companies
    auth_key_env: str = "GIGACHAT_AUTH_KEY"
    timeout_s: float = 60.0


def tls_verify() -> ssl.SSLContext | bool:
    """TLS verification setting from the environment (see module docstring)."""
    if os.environ.get("GIGACHAT_VERIFY_SSL", "").strip().lower() in ("0", "false", "no"):
        return False
    bundle = os.environ.get("GIGACHAT_CA_BUNDLE")
    if not bundle:
        return True
    ctx = ssl.create_default_context()  # system roots stay trusted, the extra root is added
    ctx.load_verify_locations(cafile=bundle)
    return ctx


class GigaChatAuth:
    """Thread-safe access-token cache: fetch on first use, refresh shortly before expiry."""

    def __init__(self, cfg: GigaChatConfig, auth_key: str, http: httpx.Client) -> None:
        self.cfg = cfg
        self._key = auth_key
        self._http = http
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def token(self) -> str:
        with self._lock:
            if self._token is None or time.time() > self._expires_at - REFRESH_MARGIN_S:
                self._refresh()
            assert self._token is not None
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def _refresh(self) -> None:
        try:
            r = self._http.post(
                self.cfg.auth_url,
                headers={
                    "Authorization": f"Basic {self._key}",
                    "RqUID": str(uuid.uuid4()),
                    "Accept": "application/json",
                },
                data={"scope": self.cfg.scope},
            )
        except httpx.HTTPError as e:
            hint = (
                " TLS verification failed: set GIGACHAT_CA_BUNDLE to the Russian Trusted Root "
                "CA file."
                if "CERTIFICATE_VERIFY_FAILED" in str(e)
                else ""
            )
            raise FatalLLMError(f"GigaChat auth request failed: {type(e).__name__}.{hint}") from e
        if r.status_code != 200:
            # The body can echo request details, so only the status is reported.
            raise FatalLLMError(
                f"GigaChat auth rejected (HTTP {r.status_code}). Check {self.cfg.auth_key_env} "
                f"and the scope ({self.cfg.scope})."
            )
        body = r.json()
        self._token = body["access_token"]
        self._expires_at = float(body["expires_at"]) / 1000.0  # the API returns milliseconds


def make_gigachat_client(cfg: GigaChatConfig | None = None) -> tuple[Any, GigaChatAuth]:
    """Return (openai.OpenAI client, auth). Every request gets a current bearer token."""
    from openai import OpenAI

    from src.config import load_dotenv

    load_dotenv()
    cfg = cfg or GigaChatConfig()
    key = os.environ.get(cfg.auth_key_env)
    if not key:
        raise FatalLLMError(f"{cfg.auth_key_env} is not set. Put the GigaChat key in .env.")
    verify = tls_verify()
    auth = GigaChatAuth(cfg, key, httpx.Client(verify=verify, timeout=cfg.timeout_s))

    def add_token(request: httpx.Request) -> None:
        request.headers["Authorization"] = f"Bearer {auth.token()}"

    http = httpx.Client(verify=verify, timeout=cfg.timeout_s, event_hooks={"request": [add_token]})
    # api_key is a placeholder: the hook above overwrites the header on every request.
    client = OpenAI(base_url=cfg.base_url, api_key="oauth", http_client=http, max_retries=0)
    return client, auth
