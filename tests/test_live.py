"""Live demo: GigaChat token handling, live feature encoding, and the HTTP API."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import numpy as np
import pandas as pd
import pytest
from catboost import CatBoostClassifier, Pool
from fastapi.testclient import TestClient

from src.features.assemble import LLM_CATEGORICAL, encode_llm
from src.features.llm_extract import FIELDS, FatalLLMError, LLMSettings
from src.live.api import Limiter, create_app
from src.live.gigachat import GigaChatAuth, GigaChatConfig
from src.live.scorer import Bundle, LiveScorer, with_reading

READING = {
    "loan_purpose_category": "business",
    "financial_stress": 3,
    "employment_stability": 1,
    "mentions_other_debts": True,
    "mentions_job_loss_or_income_drop": True,
    "mentions_medical_or_family_emergency": False,
    "has_repayment_plan": False,
    "text_quality": 2,
}
SECRET = "c2VjcmV0LWtleQ=="


# ---------------- GigaChat auth ----------------
def _auth(handler, now_ms: list[float]) -> tuple[GigaChatAuth, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request, now_ms[0])

    http = httpx.Client(transport=httpx.MockTransport(wrapped))
    return GigaChatAuth(GigaChatConfig(), SECRET, http), seen


def test_token_is_fetched_once_and_refreshed_before_expiry(monkeypatch) -> None:
    now_ms = [1_000_000_000.0]
    monkeypatch.setattr("src.live.gigachat.time.time", lambda: now_ms[0] / 1000)
    n = iter(range(100))

    def handler(_request, now):
        return httpx.Response(200, json={"access_token": f"t{next(n)}", "expires_at": now + 1.8e6})

    auth, seen = _auth(handler, now_ms)
    assert auth.token() == "t0" and auth.token() == "t0"
    assert len(seen) == 1

    req = seen[0]
    assert req.headers["Authorization"] == f"Basic {SECRET}"
    assert req.headers["RqUID"] and b"scope=GIGACHAT_API_PERS" in req.content

    now_ms[0] += 1.8e6 - 30_000  # 30 s before expiry: inside the refresh margin
    assert auth.token() == "t1"
    auth.invalidate()
    assert auth.token() == "t2"


def test_auth_failure_is_fatal_and_does_not_leak_the_key() -> None:
    auth, _ = _auth(lambda _r, _n: httpx.Response(401, text=f"bad key {SECRET}"), [0.0])
    with pytest.raises(FatalLLMError) as e:
        auth.token()
    assert "401" in str(e.value) and SECRET not in str(e.value)


# ---------------- encoding ----------------
def test_live_row_is_encoded_like_training_rows() -> None:
    """A single live reading must get the same values a training row with that reading had."""
    train = pd.DataFrame([READING, {f: None for f in FIELDS}])  # NaN row forces float upcast
    live = pd.DataFrame([READING])
    a, cats = encode_llm(train)
    b, _ = encode_llm(live)
    assert cats == [f"llm_{f}" for f in LLM_CATEGORICAL]
    assert a.iloc[0].tolist() == b.iloc[0].tolist()
    assert b["llm_employment_stability"].iloc[0] == "1"
    assert b["llm_mentions_other_debts"].iloc[0] == 1.0


# ---------------- API ----------------
class FakeClient:
    def __init__(self, reply: str | Exception) -> None:
        self.reply, self.calls = reply, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))],
            usage=SimpleNamespace(prompt_tokens=400, completion_tokens=60),
        )


@pytest.fixture(scope="module")
def bundle() -> Bundle:
    """A tiny model whose PD depends on llm_financial_stress, plus two profiles."""
    rng = np.random.default_rng(0)
    n = 400
    raw = pd.DataFrame({
        "loan_purpose_category": rng.choice(["business", "credit_card", "home"], n),
        "financial_stress": rng.integers(0, 4, n),
        "employment_stability": rng.integers(0, 4, n),
        **{f: rng.random(n) < 0.3 for f in FIELDS if f.startswith(("mentions", "has_"))},
        "text_quality": rng.integers(0, 4, n),
    })[FIELDS]  # fmt: skip
    X, cats = encode_llm(raw)
    X.insert(0, "int_rate", rng.uniform(5, 25, n))
    y = (rng.random(n) < 0.1 + 0.2 * raw["financial_stress"]).astype(int)
    model = CatBoostClassifier(iterations=40, depth=3, verbose=0, random_seed=0,
                               allow_writing_files=False)  # fmt: skip
    model.fit(Pool(X, y, cat_features=cats))
    Xp = X.iloc[:2].copy()
    Xp.index = ["p1", "p2"]
    profiles = [{"id": i, "desc": "original text"} for i in Xp.index]
    return Bundle(model, list(X.columns), cats, Xp, profiles, trained_on="trainer-llm")


CFG = {
    "live": {
        "provider": "openai_compatible", "allowed_origins": ["http://localhost:5173"],
        "max_text_chars": 200, "rate_limit_per_minute": 3, "max_requests_per_day": 100,
    }
}  # fmt: skip


def _client(bundle: Bundle, tmp_path, reply) -> tuple[TestClient, FakeClient]:
    fake = FakeClient(reply)
    s = LLMSettings(model="reader-llm", json_mode=False, transport_retries=0, backoff_s=0.0)
    scorer = LiveScorer(bundle, s, fake, tmp_path / "cache")
    return TestClient(create_app(CFG, scorer)), fake


def test_health_and_profiles(bundle, tmp_path) -> None:
    api, _ = _client(bundle, tmp_path, json.dumps(READING))
    h = api.get("/api/health").json()
    assert h["reader"] == "reader-llm" and h["trained_on"] == "trainer-llm"
    assert [p["id"] for p in api.get("/api/profiles").json()] == ["p1", "p2"]


def test_analyze_scores_the_new_reading_and_caches_it(bundle, tmp_path) -> None:
    api, fake = _client(bundle, tmp_path, json.dumps(READING))
    out = api.post("/api/analyze", json={"profile_id": "p1", "text": "I lost my job."}).json()
    assert out["reading"] == READING and out["cached"] is False

    expected = bundle.model.predict_proba(
        Pool(with_reading(bundle, "p1", READING), cat_features=bundle.categorical)
    )[0, 1]
    assert out["pd_your_text"] == pytest.approx(expected)
    assert {c["field"] for c in out["contributions"]} == set(FIELDS)

    again = api.post("/api/analyze", json={"profile_id": "p2", "text": "I lost my job."}).json()
    assert again["cached"] is True and fake.calls == 1  # same text: no second LLM call


def test_only_the_text_features_change(bundle) -> None:
    row = with_reading(bundle, "p1", READING)
    assert row["int_rate"].iloc[0] == bundle.X.loc["p1", "int_rate"]
    assert row["llm_financial_stress"].iloc[0] == 3.0
    assert list(row.dtypes) == list(bundle.X.dtypes)


def test_invalid_reading_is_scored_as_missing_not_as_an_error(bundle, tmp_path) -> None:
    api, _ = _client(bundle, tmp_path, "sorry, I cannot help with that")
    r = api.post("/api/analyze", json={"profile_id": "p1", "text": "hello"})
    assert r.status_code == 200
    assert r.json()["reading"] is None and r.json()["error"].startswith("schema")


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"profile_id": "nope", "text": "hello"}, 404),
        ({"profile_id": "p1", "text": "x" * 201}, 422),
        ({"profile_id": "p1", "text": "   "}, 422),
        ({"profile_id": "p1"}, 422),
    ],
)
def test_bad_requests_are_rejected_before_any_llm_call(bundle, tmp_path, payload, status) -> None:
    api, fake = _client(bundle, tmp_path, json.dumps(READING))
    assert api.post("/api/analyze", json=payload).status_code == status
    assert fake.calls == 0


def test_backend_failures_become_502(bundle, tmp_path) -> None:
    api, _ = _client(bundle, tmp_path, FatalLLMError("GigaChat auth rejected (HTTP 403)."))
    r = api.post("/api/analyze", json={"profile_id": "p1", "text": "hello"})
    assert r.status_code == 502 and "not available" in r.json()["detail"]

    api, _ = _client(bundle, tmp_path, RuntimeError("connection reset"))
    assert api.post("/api/analyze", json={"profile_id": "p1", "text": "hi"}).status_code == 502


def test_rate_limit_per_client(bundle, tmp_path) -> None:
    api, _ = _client(bundle, tmp_path, json.dumps(READING))
    codes = [
        api.post("/api/analyze", json={"profile_id": "p1", "text": f"text {i}"}).status_code
        for i in range(4)
    ]
    assert codes == [200, 200, 200, 429]


def test_limiter_window_and_daily_budget() -> None:
    t = [0.0]
    lim = Limiter(per_minute=2, per_day=1, now=lambda: t[0])
    assert lim.allow("a") and lim.allow("a") and not lim.allow("a")
    assert lim.allow("b")  # another client has its own window
    t[0] += 61
    assert lim.allow("a")
    assert lim.budget_left()
    lim.spend()
    assert not lim.budget_left()
    t[0] += 86400
    assert lim.budget_left()
