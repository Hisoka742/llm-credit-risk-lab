"""HTTP API for the live demo.

    GET  /api/health     is the service up, and which LLM reads the text
    GET  /api/profiles   the real test loans a visitor can pick from
    POST /api/analyze    {profile_id, text} -> LLM reading + PD before and after

The endpoint spends the owner's LLM quota, so it is rate limited per client and capped per
day. Answers are cached on disk by (model, prompt, text): a repeated text costs nothing.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.features.llm_extract import FatalLLMError, LLMSettings
from src.live.scorer import Bundle, LiveScorer


class AnalyzeRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1)


class Limiter:
    """Sliding one-minute window per client plus a daily budget for uncached reads."""

    def __init__(self, per_minute: int, per_day: int, now: Callable[[], float] = time.time) -> None:
        self.per_minute, self.per_day, self._now = per_minute, per_day, now
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._day, self._spent = 0, 0
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        with self._lock:
            now = self._now()
            q = self._hits[client]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True

    def budget_left(self) -> bool:
        with self._lock:
            day = int(self._now() // 86400)
            if day != self._day:
                self._day, self._spent = day, 0
            return self._spent < self.per_day

    def spend(self) -> None:
        with self._lock:
            self._spent += 1


def build_scorer(cfg: dict[str, Any]) -> tuple[LiveScorer, Callable[[], None]]:
    """Create the scorer for the configured provider. Returns (scorer, reset-auth callback)."""
    live = cfg["live"]
    bundle = Bundle.load(Path(cfg["paths"]["live_dir"]))
    s = LLMSettings(
        model=live["model"],
        base_url=cfg["llm"].get("base_url"),
        api_key_env=cfg["llm"]["api_key_env"],
        temperature=live["temperature"],
        max_tokens=live["max_tokens"],
        max_retries=cfg["llm"]["max_retries"],
        transport_retries=1,  # a visitor is waiting: fail fast instead of backing off
        backoff_s=1.0,
        json_mode=False,  # not every backend supports response_format; output is validated
        timeout_s=live["timeout_s"],
        max_desc_chars=live["max_text_chars"],
    )
    cache_dir = Path(cfg["paths"]["cache_dir"]) / "llm" / f"live_{s.slug}"
    if live["provider"] == "gigachat":
        from src.live.gigachat import GigaChatConfig, make_gigachat_client

        client, auth = make_gigachat_client(
            GigaChatConfig(scope=live["scope"], timeout_s=live["timeout_s"])
        )
        return LiveScorer(bundle, s, client, cache_dir), auth.invalidate
    if live["provider"] == "openai_compatible":
        from src.features.llm_extract import make_client

        return LiveScorer(bundle, s, make_client(s), cache_dir), lambda: None
    raise ValueError(f"unknown live.provider {live['provider']!r}")


def create_app(
    cfg: dict[str, Any], scorer: LiveScorer, reset_auth: Callable[[], None] = lambda: None
) -> FastAPI:
    live = cfg["live"]
    app = FastAPI(title="LLM Credit Risk Lab: live demo", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=live["allowed_origins"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    limiter = Limiter(live["rate_limit_per_minute"], live["max_requests_per_day"])

    @app.get("/")
    def root() -> dict[str, Any]:
        # Someone opened the API address in a browser: say what this is and where the page is.
        return {
            "service": "LLM Credit Risk Lab: live demo API",
            "site": live.get("site_url"),
            "endpoints": ["/api/health", "/api/profiles", "POST /api/analyze"],
        }

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "provider": live["provider"],
            "reader": scorer.s.model,
            "trained_on": scorer.b.trained_on,
            "max_text_chars": live["max_text_chars"],
        }

    @app.get("/api/profiles")
    def profiles() -> list[dict[str, Any]]:
        return scorer.b.profiles

    @app.post("/api/analyze")
    def analyze(req: AnalyzeRequest, request: Request) -> dict[str, Any]:
        text = req.text.strip()
        if not text:
            raise HTTPException(422, "The description is empty.")
        if len(text) > live["max_text_chars"]:
            raise HTTPException(422, f"Keep the description under {live['max_text_chars']} "
                                     "characters.")  # fmt: skip
        if not scorer.has_profile(req.profile_id):
            raise HTTPException(404, "Unknown profile.")
        client = request.client.host if request.client else "unknown"
        if live.get("trust_proxy"):
            # Behind a hosting platform's proxy every request comes from the proxy's address.
            # The visitor's address is the first entry of X-Forwarded-For. Only trusted when
            # configured, because a direct client could forge the header.
            forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            client = forwarded or client
        if not limiter.allow(client):
            raise HTTPException(429, "Too many requests. Wait a minute and try again.")
        if not limiter.budget_left():
            raise HTTPException(429, "The demo's daily budget is used up. Try again tomorrow.")

        try:
            try:
                out = scorer.analyze(req.profile_id, text)
            except FatalLLMError as e:
                if "401" not in str(e):
                    raise
                reset_auth()  # token revoked or expired early: fetch a new one, try once more
                out = scorer.analyze(req.profile_id, text)
        except FatalLLMError as e:
            raise HTTPException(502, f"The language model is not available: {e}") from e
        if not out["cached"]:
            limiter.spend()
        if out["reading"] is None and (out["error"] or "").startswith("api"):
            raise HTTPException(502, "The language model did not answer. Try again.")
        return out

    return app
