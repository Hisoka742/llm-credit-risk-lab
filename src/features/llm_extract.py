"""LLM extraction of structured features from `desc` via any OpenAI-compatible endpoint.

Works with vLLM (`vllm serve ...`), OpenAI, OpenRouter, Ollama (`/v1`), or a GigaChat
OpenAI-compatible proxy. Only `base_url`, `model` and the API-key env var change.

Reliability rules (CLAUDE.md):
- Output is validated against `LoanTextFeatures` (pydantic). An invalid answer gets one retry,
  with the validation error fed back to the model. If that also fails, the result is null.
- Every final result is cached on disk, including nulls, keyed by
  sha256(model + system prompt + user prompt). Reruns cost nothing, and any prompt change
  invalidates the cache automatically.
- Transient transport errors (timeouts, connection errors, rate-limit 429, 5xx) are retried here
  with exponential backoff. That is separate from the schema retry, and a call that still fails
  gives a null that is NOT cached, so the next run tries again.
- Fatal errors (bad key, no credits, unknown model, rejected parameter) raise FatalLLMError
  and stop the whole run. Retrying them would only produce 125k nulls.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

PurposeCategory = Literal[
    "debt_consolidation", "credit_card", "home", "business", "medical", "education", "car", "other"
]


class LoanTextFeatures(BaseModel):
    """Schema from CLAUDE.md. Extra keys are ignored, and missing or out-of-range keys fail."""

    model_config = ConfigDict(extra="ignore")

    loan_purpose_category: PurposeCategory
    financial_stress: int = Field(ge=0, le=3)
    employment_stability: int = Field(ge=0, le=3)
    mentions_other_debts: bool
    mentions_job_loss_or_income_drop: bool
    mentions_medical_or_family_emergency: bool
    has_repayment_plan: bool
    text_quality: int = Field(ge=0, le=3)


FIELDS = list(LoanTextFeatures.model_fields)


class FatalLLMError(RuntimeError):
    """Configuration or account problem: every further request would fail the same way."""


def _is_fatal(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    code = getattr(e, "code", None)
    if code in ("insufficient_quota", "credit_balance_exhausted", "invalid_api_key"):
        return True  # 429 from OpenAI when out of credits: waiting will not help
    if status in (401, 402, 403, 404):  # 402 = payment required (e.g. OpenRouter credits)
        return True
    # A 400 naming a parameter (e.g. temperature unsupported by a reasoning model) is a config
    # error. A 400 without one may be specific to one text, so it only nulls that row.
    return status == 400 and getattr(e, "param", None) is not None


def _is_transient(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    name = type(e).__name__
    return (
        status in (408, 409, 429) or (status is not None and status >= 500)
        or name in ("APITimeoutError", "APIConnectionError", "TimeoutError")
    )  # fmt: skip


# Scale anchors are spelled out: vague scales ("rate 0-3") make small models drift
# between runs and between borrowers. employment_stability 0 means "not mentioned", which
# is not "unstable". Downstream it should be treated as categorical, not ordinal.
SYSTEM_PROMPT = """\
You extract structured facts from a peer-to-peer loan applicant's free-text description.
Judge ONLY from the text. Do not guess facts that are not stated.
Return ONE JSON object with exactly these keys:

loan_purpose_category: one of "debt_consolidation", "credit_card", "home", "business",
  "medical", "education", "car", "other". Use credit_card when the loan pays off credit
  cards specifically, debt_consolidation for several debts or unspecified consolidation.
financial_stress: integer 0-3. 0 = no sign of stress, 1 = mild (wants a lower rate), 2 = clear
  strain (behind on bills, high balances hurting them), 3 = severe (collections, default,
  eviction, bankruptcy risk).
employment_stability: integer 0-3. 0 = employment not mentioned, 1 = unstable (new job,
  temporary, recently unemployed), 2 = employed with no detail, 3 = clearly stable (long
  tenure, permanent or government position, stated years in the job).
mentions_other_debts: true if the text mentions existing debts (cards, loans, medical bills).
mentions_job_loss_or_income_drop: true if the text mentions job loss, reduced hours or pay,
  or lost income.
mentions_medical_or_family_emergency: true if the text mentions illness, medical bills,
  a death, a divorce, or another family emergency.
has_repayment_plan: true if the borrower describes HOW they will repay (budget, income
  source, payoff timeline).
text_quality: integer 0-3. 0 = empty or unintelligible, 1 = a few words or incoherent,
  2 = understandable but brief, 3 = clear, specific and coherent.

Output only the JSON object, with no markdown and no commentary."""

USER_TEMPLATE = "Loan description:\n<<<\n{text}\n>>>"


@dataclass(frozen=True)
class LLMSettings:
    model: str
    base_url: str | None = None
    api_key_env: str = "LLM_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 256
    max_retries: int = 1  # schema retries after the first attempt
    transport_retries: int = 4  # backoff retries for transient API errors
    backoff_s: float = 2.0
    json_mode: bool = True  # response_format={"type": "json_object"}, if the server supports it
    timeout_s: float = 60.0
    max_desc_chars: int = 4000
    concurrency: int = 8
    # Provider-specific request fields, e.g. {"reasoning": {"enabled": false}} on OpenRouter or
    # {"chat_template_kwargs": {"enable_thinking": false}} on vLLM for Qwen3 thinking models.
    extra_body: dict[str, Any] | None = None
    max_rpm: float | None = None  # client-side request rate cap (provider limit), None = off
    # Stop the run when this many requests in a row fail at the API level (after backoff):
    # the server is down, and carrying on only turns every remaining loan into a null.
    max_consecutive_api_errors: int = 50

    @property
    def slug(self) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", self.model.split("/")[-1])


@dataclass
class ExtractResult:
    key: str
    features: dict[str, Any] | None
    attempts: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    raw: list[str] = field(default_factory=list)
    error: str | None = None
    cached: bool = False


def build_messages(text: str, s: LLMSettings) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(text=text[: s.max_desc_chars])},
    ]


def cache_key(s: LLMSettings, messages: list[dict[str, str]]) -> str:
    payload = json.dumps(
        {"model": s.model, "temperature": s.temperature, "messages": messages,
         "extra_body": s.extra_body},
        sort_keys=True,
    )  # fmt: skip
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_response(text: str) -> LoanTextFeatures:
    """Parse model output into the schema. Tolerates code fences and prose around the JSON."""
    t = _FENCE.sub("", (text or "").strip())
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    return LoanTextFeatures.model_validate(json.loads(t[start : end + 1]))


class DiskCache:
    """One JSON file per key under 2-char shard directories. Writes are atomic (tmp + replace),
    so a killed notebook never leaves a corrupt entry."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        p = self._path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)


def make_client(s: LLMSettings):  # -> openai.OpenAI
    import os

    from openai import OpenAI

    from src.config import load_dotenv

    load_dotenv()

    return OpenAI(
        base_url=s.base_url or os.environ.get("LLM_BASE_URL"),
        # Local vLLM/Ollama servers accept any key. Hosted APIs need the env var.
        api_key=os.environ.get(s.api_key_env) or os.environ.get("OPENAI_API_KEY") or "EMPTY",
        timeout=s.timeout_s,
        # Our own loop does the retries, so fatal errors such as "no credits" (also a 429)
        # are not retried blindly.
        max_retries=0,
    )


class RateLimiter:
    """Thread-safe request pacing: at most `rpm` request starts per minute, evenly spaced.

    Staying under the provider limit is cheaper than hitting 429s and backing off. Backoff
    sleeps would also inflate the measured latency.
    """

    def __init__(self, rpm: float | None) -> None:
        self.interval = 60.0 / rpm if rpm else 0.0
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        if not self.interval:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self.interval
        time.sleep(max(0.0, start - now))


_NO_LIMIT = RateLimiter(None)


def _create(
    client: Any, s: LLMSettings, limiter: RateLimiter = _NO_LIMIT, **kwargs: Any
) -> tuple[Any, float]:
    """Return (response, latency of the successful request only, excluding waits)."""
    for i in range(s.transport_retries + 1):
        limiter.wait()
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(**kwargs)
            return resp, time.perf_counter() - t0
        except Exception as e:
            if _is_fatal(e):
                raise FatalLLMError(f"{type(e).__name__}: {e}") from e
            if not _is_transient(e) or i == s.transport_retries:
                raise
            time.sleep(s.backoff_s * 2**i)


def extract_one(
    text: str,
    s: LLMSettings,
    client: Any,
    cache: DiskCache,
    refresh_failed: bool = False,
    limiter: RateLimiter = _NO_LIMIT,
) -> ExtractResult:
    messages = build_messages(text, s)
    key = cache_key(s, messages)
    hit = cache.get(key)
    if hit is not None and not (refresh_failed and hit["features"] is None):
        return ExtractResult(**{**hit, "cached": True})

    res = ExtractResult(key=key, features=None, attempts=0)
    convo = list(messages)
    kwargs: dict[str, Any] = {"response_format": {"type": "json_object"}} if s.json_mode else {}
    if s.extra_body:
        kwargs["extra_body"] = s.extra_body
    for _ in range(1 + s.max_retries):
        res.attempts += 1
        try:
            resp, latency = _create(
                client,
                s,
                limiter,
                model=s.model,
                messages=convo,
                temperature=s.temperature,
                max_tokens=s.max_tokens,
                **kwargs,
            )
        except FatalLLMError:
            raise
        except Exception as e:  # still failing after backoff: null for this row, not cached
            cause = (
                f" (cause: {e.__cause__!r})" if e.__cause__ else ""
            )  # "Connection error." alone hides why
            res.error = f"api: {type(e).__name__}: {e}{cause}"
            return res
        res.latency_s += latency
        if resp.usage is not None:
            res.prompt_tokens += resp.usage.prompt_tokens or 0
            res.completion_tokens += resp.usage.completion_tokens or 0
        choice = resp.choices[0]
        content = choice.message.content or ""
        res.raw.append(content)
        if getattr(choice, "finish_reason", None) == "length" and "}" not in content:
            # Typical of reasoning models spending the budget on thinking. Retrying with the
            # same budget will not help: raise max_tokens or disable thinking via extra_body.
            res.error = f"truncated at max_tokens={s.max_tokens} before any JSON"
            break
        try:
            res.features = parse_response(content).model_dump()
            res.error = None
            break
        except (ValueError, ValidationError) as e:
            res.error = f"schema: {str(e)[:500]}"
            convo = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": f"Invalid output: {str(e)[:500]}\n"
                    "Return only the corrected JSON object.",
                },  # fmt: skip
            ]

    record = asdict(res)
    record.pop("cached")
    cache.put(key, record)
    return res


def extract_many(
    texts: Iterable[str], s: LLMSettings, cache_dir: Path, client: Any = None,
    refresh_failed: bool = False, progress_every: int = 500,
) -> list[ExtractResult]:  # fmt: skip
    texts = list(texts)
    client = client or make_client(s)
    cache = DiskCache(cache_dir)
    limiter = RateLimiter(s.max_rpm)
    out: list[ExtractResult | None] = [None] * len(texts)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=s.concurrency) as pool:
        futures = {
            pool.submit(extract_one, t, s, client, cache, refresh_failed, limiter): i
            for i, t in enumerate(texts)
        }
        # Count in completion order: iterating futures in submission order let one slow request
        # freeze the counter for minutes while hundreds of later requests had finished.
        n_new = n_failed = streak = 0
        for n_done, fut in enumerate(as_completed(futures), start=1):
            try:
                res = fut.result()
            except FatalLLMError:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            out[futures[fut]] = res
            if (res.error or "").startswith("api"):
                n_failed += 1
                streak += 1
                if streak >= s.max_consecutive_api_errors:
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise FatalLLMError(
                        f"{streak} requests in a row failed at the API ({res.error}); the "
                        "endpoint looks down. Answers so far are cached: restart it and rerun."
                    )
            elif not res.cached:
                n_new += 1
                streak = 0
            if n_done % progress_every == 0 or n_done == len(texts):
                rate = n_new / (time.perf_counter() - t0)
                print(
                    f"[llm] {n_done:,}/{len(texts):,} done ({n_new:,} new, {rate:.1f} new/s, "
                    f"{n_failed:,} failed)",
                    flush=True,
                )
    return out  # type: ignore[return-value]


def results_frame(ids: pd.Series, results: list[ExtractResult]) -> pd.DataFrame:
    """One row per loan: schema fields (NaN when null) plus status columns."""
    rows = []
    for r in results:
        row = dict.fromkeys(FIELDS) if r.features is None else dict(r.features)
        row.update(llm_ok=r.features is not None, llm_attempts=r.attempts, llm_error=r.error)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "id", ids.to_numpy())
    return df


def cost_summary(
    results: list[ExtractResult],
    s: LLMSettings,
    prices: dict,
    wall_s: float | None = None,
    hardware: str | None = None,
) -> dict[str, Any]:
    """Token and latency stats over *fresh* calls only. Cache hits cost nothing and would
    distort per-application latency."""
    api_errors = [r for r in results if (r.error or "").startswith("api")]
    fresh = [r for r in results if not r.cached and r.attempts > 0 and r not in api_errors]
    summary: dict[str, Any] = {
        "model": s.model,
        "n": len(results),
        "n_fresh_calls": len(fresh),
        "n_cached": sum(r.cached for r in results),
        "n_api_errors": len(api_errors),
        "valid_rate": float(np.mean([r.features is not None for r in results]))
        if results
        else None,
        "retry_rate": float(np.mean([r.attempts > 1 for r in fresh])) if fresh else None,
    }  # fmt: skip
    if fresh:
        lat = np.array([r.latency_s for r in fresh])
        pt = np.array([r.prompt_tokens for r in fresh])
        ct = np.array([r.completion_tokens for r in fresh])
        summary.update(
            mean_prompt_tokens=float(pt.mean()),
            mean_completion_tokens=float(ct.mean()),
            latency_mean_s=float(lat.mean()),
            latency_p50_s=float(np.median(lat)),
            latency_p95_s=float(np.quantile(lat, 0.95)),
            concurrency=s.concurrency,
            hardware=hardware,
        )
    if fresh and wall_s:
        # For a self-hosted model the honest unit is accelerator time: wall time over fresh
        # calls, with requests batched by the server at the given concurrency.
        summary.update(
            wall_seconds=round(wall_s, 1),
            throughput_per_s=len(fresh) / wall_s,
            accelerator_seconds_per_application=wall_s / len(fresh),
        )
    pin, pout = prices.get("usd_per_1m_input"), prices.get("usd_per_1m_output")
    if fresh and pin is not None and pout is not None:
        summary["usd_per_application"] = float(
            (summary["mean_prompt_tokens"] * pin + summary["mean_completion_tokens"] * pout) / 1e6
        )
    return summary


def select_sample(df: pd.DataFrame, n: int | None, seed: int) -> pd.Series:
    """Fixed, split-stratified sample of loan ids for LLM extraction (shared by E2 and E3).

    Stratifying by split keeps the 70/15/15 proportions, so every split has LLM features.
    """
    if n is None or n >= len(df):
        return df["id"].reset_index(drop=True)
    frac = n / len(df)
    parts = [
        g.sample(n=max(1, round(len(g) * frac)), random_state=seed)
        for _, g in df.groupby("split", observed=True)
    ]
    return pd.concat(parts)["id"].reset_index(drop=True)


def shard_mask(texts: pd.Series, i: int, n: int) -> pd.Series:
    """True for rows in shard i of n. Sharding is by *text*, so identical descriptions always
    land in the same shard and two GPUs never generate the same answer twice."""
    if not 0 <= i < n:
        raise ValueError(f"shard {i}/{n} out of range")
    h = texts.astype(str).map(lambda t: int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16))
    return h % n == i


def merge_costs(costs: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-shard cost summaries (one shard per GPU) into one cost record.

    Accelerator time adds up across GPUs: GPU-seconds per application = sum(wall) / sum(calls).
    Throughput adds up too, because the shards ran in parallel.
    """
    fresh = [c for c in costs if c.get("n_fresh_calls")]
    if not fresh:
        return {}
    w = np.array([c["n_fresh_calls"] for c in fresh], dtype=float)

    def wmean(key: str) -> float:
        return float(np.average([c[key] for c in fresh], weights=w))

    return {
        "model": fresh[0]["model"],
        "n_shards": len(fresh),
        "n_fresh_calls": int(w.sum()),
        "n_api_errors": int(sum(c.get("n_api_errors", 0) for c in fresh)),
        "retry_rate": wmean("retry_rate"),
        "mean_prompt_tokens": wmean("mean_prompt_tokens"),
        "mean_completion_tokens": wmean("mean_completion_tokens"),
        "latency_mean_s": wmean("latency_mean_s"),
        # Per-shard percentiles cannot be merged exactly; this is their call-weighted mean.
        "latency_p50_s": wmean("latency_p50_s"),
        "latency_p95_s": wmean("latency_p95_s"),
        "concurrency": fresh[0].get("concurrency"),
        "hardware": f"{len(fresh)} x " + str(fresh[0].get("hardware")),
        "wall_seconds": max(c["wall_seconds"] for c in fresh),
        "throughput_per_s": float(sum(c["throughput_per_s"] for c in fresh)),
        "accelerator_seconds_per_application": float(
            sum(c["wall_seconds"] for c in fresh) / w.sum()
        ),
    }
