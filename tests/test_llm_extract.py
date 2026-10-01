from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest
from pydantic import ValidationError

from src.features.llm_extract import (
    FIELDS,
    DiskCache,
    LLMSettings,
    LoanTextFeatures,
    build_messages,
    cache_key,
    cost_summary,
    extract_many,
    extract_one,
    parse_response,
    results_frame,
    select_sample,
)

VALID = {
    "loan_purpose_category": "credit_card",
    "financial_stress": 1,
    "employment_stability": 3,
    "mentions_other_debts": True,
    "mentions_job_loss_or_income_drop": False,
    "mentions_medical_or_family_emergency": False,
    "has_repayment_plan": True,
    "text_quality": 2,
}


class FakeClient:
    """Mimics openai.OpenAI().chat.completions.create with scripted replies."""

    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(prompt_tokens=400, completion_tokens=60),
        )


S = LLMSettings(model="fake-model", concurrency=2, backoff_s=0.0)  # no real sleeping in tests


def test_schema_matches_claude_md() -> None:
    assert list(VALID) == FIELDS
    assert LoanTextFeatures(**VALID).financial_stress == 1


@pytest.mark.parametrize(
    "bad",
    [
        {**VALID, "financial_stress": 4},
        {**VALID, "text_quality": -1},
        {**VALID, "loan_purpose_category": "vacation"},
        {k: v for k, v in VALID.items() if k != "has_repayment_plan"},
    ],
)
def test_schema_rejects_invalid(bad) -> None:
    with pytest.raises(ValidationError):
        LoanTextFeatures(**bad)


def test_parse_tolerates_fences_and_prose() -> None:
    assert parse_response("```json\n" + json.dumps(VALID) + "\n```").text_quality == 2
    assert parse_response("Sure! " + json.dumps(VALID) + " Hope this helps").text_quality == 2
    with pytest.raises(ValueError):
        parse_response("I cannot help with that")


def test_valid_first_try_is_cached(tmp_path) -> None:
    client = FakeClient([json.dumps(VALID)])
    cache = DiskCache(tmp_path)
    r = extract_one("pay off my cards", S, client, cache)
    assert r.features == VALID and r.attempts == 1 and not r.cached
    assert (r.prompt_tokens, r.completion_tokens) == (400, 60)
    assert client.calls[0]["response_format"] == {"type": "json_object"}
    r2 = extract_one("pay off my cards", S, client, cache)
    assert r2.cached and r2.features == VALID and len(client.calls) == 1


def test_invalid_then_valid_retries_once_with_error_feedback(tmp_path) -> None:
    client = FakeClient(["not json", json.dumps(VALID)])
    r = extract_one("text", S, client, DiskCache(tmp_path))
    assert r.features == VALID and r.attempts == 2 and r.error is None
    retry_msgs = client.calls[1]["messages"]
    assert retry_msgs[-2] == {"role": "assistant", "content": "not json"}
    assert "Invalid output" in retry_msgs[-1]["content"]
    assert r.prompt_tokens == 800  # tokens summed over both attempts


def test_invalid_twice_gives_cached_null(tmp_path) -> None:
    client = FakeClient([json.dumps({**VALID, "financial_stress": 9})])
    cache = DiskCache(tmp_path)
    r = extract_one("text", S, client, cache)
    assert r.features is None and r.attempts == 2 and r.error.startswith("schema")
    assert extract_one("text", S, client, cache).cached  # null is cached: reruns are free
    extract_one("text", S, FakeClient([json.dumps(VALID)]), cache, refresh_failed=True)
    assert extract_one("text", S, client, cache).features == VALID


def test_transport_error_is_not_cached(tmp_path) -> None:
    cache = DiskCache(tmp_path)
    r = extract_one("text", S, FakeClient([TimeoutError("boom")]), cache)
    assert r.features is None and r.error.startswith("api")
    assert extract_one("text", S, FakeClient([json.dumps(VALID)]), cache).features == VALID


def test_cache_key_depends_on_model_and_prompt() -> None:
    m = build_messages("hello", S)
    assert cache_key(S, m) == cache_key(S, build_messages("hello", S))
    assert cache_key(S, m) != cache_key(LLMSettings(model="other"), m)
    assert cache_key(S, m) != cache_key(S, build_messages("hello!", S))


def test_extract_many_keeps_order_and_frames(tmp_path) -> None:
    client = FakeClient([json.dumps(VALID)])
    res = extract_many(["a", "b", "a"], S, tmp_path, client=client)
    assert [r.features for r in res] == [VALID] * 3
    df = results_frame(pd.Series(["1", "2", "3"]), res)
    assert list(df.columns[:1]) == ["id"] and df["llm_ok"].all()
    cost = cost_summary(res, S, {"usd_per_1m_input": 1.0, "usd_per_1m_output": 2.0})
    assert cost["valid_rate"] == 1.0
    assert cost["usd_per_application"] == pytest.approx((400 * 1 + 60 * 2) / 1e6)


def test_select_sample_is_fixed_and_stratified() -> None:
    df = pd.DataFrame({"id": [str(i) for i in range(1000)],
                       "split": ["train"] * 700 + ["val"] * 150 + ["test"] * 150})  # fmt: skip
    a, b = select_sample(df, 100, seed=1), select_sample(df, 100, seed=1)
    assert a.tolist() == b.tolist()
    counts = df.set_index("id").loc[a, "split"].value_counts()
    assert counts.to_dict() == {"train": 70, "val": 15, "test": 15}


def test_load_dotenv_does_not_override(tmp_path, monkeypatch) -> None:
    from src.config import load_dotenv

    env = tmp_path / ".env"
    env.write_text("# c\nFOO_TEST_A='x'\nFOO_TEST_B=file\n", encoding="utf-8")
    monkeypatch.delenv("FOO_TEST_A", raising=False)
    monkeypatch.setenv("FOO_TEST_B", "shell")
    load_dotenv(env)
    import os

    assert os.environ["FOO_TEST_A"] == "x" and os.environ["FOO_TEST_B"] == "shell"


class FakeAPIError(Exception):
    def __init__(self, status_code: int, code: str | None = None, param: str | None = None):
        super().__init__(f"{status_code} {code}")
        self.status_code, self.code, self.param = status_code, code, param


@pytest.mark.parametrize(
    "err",
    [FakeAPIError(429, "insufficient_quota"), FakeAPIError(401), FakeAPIError(402),
     FakeAPIError(404), FakeAPIError(400, param="temperature")],
)  # fmt: skip
def test_fatal_errors_stop_the_run_without_retry(tmp_path, err) -> None:
    from src.features.llm_extract import FatalLLMError

    client = FakeClient([err])
    with pytest.raises(FatalLLMError):
        extract_many(["a", "b", "c"], S, tmp_path, client=client)
    # Workers already in flight may each make one call before cancellation, but no text is retried.
    texts = [c["messages"][-1]["content"] for c in client.calls]
    assert len(texts) == len(set(texts))
    assert not any(tmp_path.rglob("*.json"))  # nothing cached


def test_transient_errors_back_off_then_succeed(tmp_path) -> None:
    from dataclasses import replace

    s = replace(S, backoff_s=0.0)
    client = FakeClient([FakeAPIError(429, "rate_limit_exceeded"), FakeAPIError(503),
                         json.dumps(VALID)])  # fmt: skip
    r = extract_one("text", s, client, DiskCache(tmp_path))
    assert r.features == VALID and len(client.calls) == 3


def test_cost_summary_excludes_api_failures(tmp_path) -> None:
    from dataclasses import replace

    s = replace(S, transport_retries=0)
    ok = extract_one("a", s, FakeClient([json.dumps(VALID)]), DiskCache(tmp_path))
    bad = extract_one("b", s, FakeClient([FakeAPIError(500)]), DiskCache(tmp_path))
    c = cost_summary([ok, bad], s, {})
    assert c["n_fresh_calls"] == 1 and c["n_api_errors"] == 1
    assert c["mean_prompt_tokens"] == 400


def test_truncated_reasoning_output_is_not_retried(tmp_path) -> None:
    class Truncating(FakeClient):
        def _create(self, **kwargs):
            r = super()._create(**kwargs)
            r.choices[0].finish_reason = "length"
            return r

    client = Truncating(["<think>Let me consider the borrower's"])
    r = extract_one("text", S, client, DiskCache(tmp_path))
    assert r.features is None and r.attempts == 1 and "truncated" in r.error


def test_extra_body_is_sent_and_changes_cache_key(tmp_path) -> None:
    from dataclasses import replace

    s = replace(S, extra_body={"reasoning": {"enabled": False}})
    client = FakeClient([json.dumps(VALID)])
    extract_one("t", s, client, DiskCache(tmp_path))
    assert client.calls[0]["extra_body"] == {"reasoning": {"enabled": False}}
    m = build_messages("t", S)
    assert cache_key(s, m) != cache_key(S, m)


def test_rate_limiter_spaces_requests() -> None:
    import threading
    import time

    from src.features.llm_extract import RateLimiter

    lim = RateLimiter(rpm=600)  # one start every 0.1 s
    starts: list[float] = []
    lock = threading.Lock()

    def go() -> None:
        lim.wait()
        with lock:
            starts.append(time.monotonic())

    threads = [threading.Thread(target=go) for _ in range(5)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    # Five starts at one per 0.1 s must span at least four intervals. Checking the total span
    # (not each gap) keeps the test stable when the machine is busy and a thread wakes late.
    assert max(starts) - min(starts) >= 0.38
    assert len({round(s, 3) for s in starts}) == 5  # no two callers released together
    assert RateLimiter(None).interval == 0.0


def test_latency_excludes_backoff_wait(tmp_path) -> None:
    from dataclasses import replace

    s = replace(S, backoff_s=0.3)
    client = FakeClient([FakeAPIError(429, "rate_limit_exceeded"), json.dumps(VALID)])
    r = extract_one("text", s, client, DiskCache(tmp_path))
    assert r.features == VALID and r.latency_s < 0.2  # the 0.3 s backoff is not latency


def test_cost_summary_accelerator_seconds(tmp_path) -> None:
    res = extract_many(["a", "b"], S, tmp_path, client=FakeClient([json.dumps(VALID)]))
    c = cost_summary(res, S, {}, wall_s=4.0, hardware="T4")
    assert c["accelerator_seconds_per_application"] == 2.0 and c["hardware"] == "T4"
    assert "usd_per_application" not in c


def test_shards_partition_texts_without_overlap() -> None:
    from src.features.llm_extract import shard_mask

    texts = pd.Series(["debt"] * 3 + [f"text {i}" for i in range(200)])
    masks = [shard_mask(texts, i, 2) for i in range(2)]
    assert (masks[0] ^ masks[1]).all()  # every row in exactly one shard
    assert masks[0][:3].nunique() == 1  # identical texts share a shard
    assert 60 < masks[0].sum() < 140  # roughly balanced
    with pytest.raises(ValueError):
        shard_mask(texts, 2, 2)


def test_merge_costs_adds_gpu_time_and_throughput() -> None:
    from src.features.llm_extract import merge_costs

    base = {
        "model": "m",
        "retry_rate": 0.0,
        "mean_prompt_tokens": 500.0,
        "mean_completion_tokens": 80.0,
        "latency_mean_s": 4.0,
        "latency_p50_s": 4.0,
        "latency_p95_s": 6.0,
        "concurrency": 64,
        "hardware": "T4",
        "n_api_errors": 0,
    }
    a = {**base, "n_fresh_calls": 100, "wall_seconds": 50.0, "throughput_per_s": 2.0}
    b = {**base, "n_fresh_calls": 300, "wall_seconds": 100.0, "throughput_per_s": 3.0}
    m = merge_costs([a, b])
    assert m["n_fresh_calls"] == 400 and m["throughput_per_s"] == 5.0
    assert m["accelerator_seconds_per_application"] == pytest.approx(150 / 400)
    assert m["wall_seconds"] == 100.0 and m["hardware"] == "2 x T4"


def test_dead_endpoint_stops_the_run(tmp_path) -> None:
    from dataclasses import replace

    from src.features.llm_extract import FatalLLMError

    s = replace(S, transport_retries=0, max_consecutive_api_errors=5)
    client = FakeClient([FakeAPIError(503)])  # every call fails like a crashed server
    with pytest.raises(FatalLLMError, match="endpoint looks down"):
        extract_many([f"t{i}" for i in range(40)], s, tmp_path, client=client)
    assert len(client.calls) < 40  # stopped early instead of failing every loan


def test_isolated_api_errors_do_not_stop_the_run(tmp_path) -> None:
    from dataclasses import replace

    s = replace(S, transport_retries=0, max_consecutive_api_errors=3, concurrency=1)
    replies = [FakeAPIError(503), json.dumps(VALID)] * 5  # alternating: never 3 in a row
    client = FakeClient(replies + [json.dumps(VALID)])
    res = extract_many([f"t{i}" for i in range(10)], s, tmp_path, client=client)
    assert sum(r.features is None for r in res) == 5
