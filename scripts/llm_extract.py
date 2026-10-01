"""Extract structured LLM features from `desc` for the fixed LLM sample.

    python -m scripts.llm_extract --config configs/e2.yaml --n 20 --show   # inspect first
    python -m scripts.llm_extract --config configs/e2.yaml                 # full sample

Backend: any OpenAI-compatible server. Set `llm.base_url` / `llm.model` in the config, or the
LLM_BASE_URL env var, and the key in the env var named by `llm.api_key_env`.

Writes data/processed/llm_features/<model>.parquet, data/processed/llm_sample_ids.parquet
(fixed on first run so E2 and E3 share it) and reports/runs/llm_<model>/cost.json.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

from src.config import load_config, load_dotenv
from src.features.llm_extract import (
    FatalLLMError,
    LLMSettings,
    cost_summary,
    extract_many,
    merge_costs,
    results_frame,
    select_sample,
    shard_mask,
)


def _settings(cfg: dict, args: argparse.Namespace) -> LLMSettings:
    c = cfg["llm"]
    return LLMSettings(
        model=args.model or c["model"],
        base_url=args.base_url or c["base_url"],
        api_key_env=c["api_key_env"],
        temperature=c["temperature"],
        max_tokens=c["max_tokens"],
        max_retries=c["max_retries"],
        json_mode=c["json_mode"] if args.json_mode is None else args.json_mode == "on",
        timeout_s=c["timeout_s"],
        max_desc_chars=c["max_desc_chars"],
        concurrency=args.concurrency or c["concurrency"],
        extra_body=c.get("extra_body"),
        max_rpm=args.max_rpm or c.get("max_rpm"),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/e2.yaml")
    ap.add_argument("--n", type=int, default=None, help="only the first N loans of the sample")
    ap.add_argument("--show", action="store_true", help="print each description with its JSON")
    ap.add_argument("--model", default=None, help="override llm.model")
    ap.add_argument("--base-url", default=None, help="override llm.base_url")
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--max-rpm", type=float, default=None, help="override llm.max_rpm")
    ap.add_argument("--json-mode", choices=["on", "off"], default=None,
                    help="override llm.json_mode (constrained decoding)")  # fmt: skip
    ap.add_argument("--hardware", default=None,
                    help='label for the cost table, e.g. "Kaggle T4, vLLM, AWQ"')  # fmt: skip
    ap.add_argument("--refresh-failed", action="store_true", help="re-query cached nulls")
    ap.add_argument(
        "--shard",
        default=None,
        metavar="I/N",
        help="process only shard I of N (split by text, so shards never duplicate "
        "work); run one per GPU, then once without --shard to assemble",
    )
    ap.add_argument(
        "--merge-shard-costs",
        action="store_true",
        help="combine cost.shard*.json into cost.json (use on the assembling run)",
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    s = _settings(cfg, args)
    processed = Path(cfg["paths"]["processed"])
    df = pd.read_parquet(processed, columns=["id", "desc", "split", "target"])

    sample_path = processed.parent / "llm_sample_ids.parquet"
    size = cfg["llm"]["sample_size"]
    if sample_path.exists():
        ids = pd.read_parquet(sample_path)["id"]
        expected = len(df) if size is None else size
        if abs(len(ids) - expected) > 3:  # per-split rounding can shift the size by a few
            raise ValueError(
                f"{sample_path} has {len(ids)} ids but llm.sample_size={size}. "
                "Delete it to draw a new sample (E2/E3 must then be rerun)."
            )
    else:
        ids = select_sample(df, size, cfg["seed"])
        # Shuffle once so that `--n 20` sees a random mix of years and splits.
        ids = ids.sample(frac=1, random_state=cfg["seed"]).reset_index(drop=True)
        ids.to_frame().to_parquet(sample_path, index=False)
        print(f"[llm] fixed sample of {len(ids):,} loans -> {sample_path}")
    if args.n:
        ids = ids.head(args.n)
    rows = df.set_index("id").loc[ids.to_numpy()].reset_index()
    shard_tag = ""
    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        rows = rows[shard_mask(rows["desc"], i, n)].reset_index(drop=True)
        shard_tag = f".shard{i}of{n}"

    cache_dir = Path(cfg["paths"]["cache_dir"]) / "llm" / s.slug
    load_dotenv()
    endpoint = s.base_url or os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1"
    print(f"[llm] {len(rows):,} descriptions -> {s.model} @ {endpoint}", flush=True)
    try:
        t0 = time.perf_counter()
        results = extract_many(rows["desc"], s, cache_dir, refresh_failed=args.refresh_failed)
        wall_s = time.perf_counter() - t0
    except FatalLLMError as e:
        raise SystemExit(f"[llm] stopped, nothing written: {e}") from None
    n_api = sum((r.error or "").startswith("api") for r in results)
    if n_api and not args.n:
        # Failed requests are not cached, so a rerun retries exactly these. Writing the feature
        # file now would hand E2 nulls that mean "server was down", not "model had no answer".
        raise SystemExit(
            f"[llm] {n_api:,} requests failed at the API; feature file NOT written. "
            "Rerun (answers so far are cached) once the endpoint is healthy."
        )
    feats = results_frame(rows["id"], results)

    out = processed.parent / "llm_features" / f"{s.slug}.parquet"
    if args.n or shard_tag:
        out = out.with_name(f"{s.slug}{f'.n{args.n}' if args.n else ''}{shard_tag}.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(out, index=False)

    cost = cost_summary(results, s, cfg["llm"], wall_s=wall_s, hardware=args.hardware)
    run_dir = Path(cfg["paths"]["reports_dir"]) / "runs" / f"llm_{s.slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.merge_shard_costs:
        shard_costs = [json.loads(f.read_text()) for f in sorted(run_dir.glob("cost.shard*.json"))]
        if shard_costs:
            cost = {**merge_costs(shard_costs), "n": cost["n"], "valid_rate": cost["valid_rate"]}
            (run_dir / "cost.json").write_text(json.dumps(cost, indent=2))
    elif cost["n_fresh_calls"]:
        name = f"cost{f'.n{args.n}' if args.n else ''}{shard_tag}.json"
        (run_dir / name).write_text(json.dumps(cost, indent=2))

    if args.show:
        for (_, r), res in zip(rows.iterrows(), results, strict=True):
            text = r["desc"] if len(r["desc"]) <= 600 else r["desc"][:600] + " …"
            print(f"\n--- id {r['id']} | {r['split']} | target {r['target']} | "
                  f"{res.prompt_tokens}+{res.completion_tokens} tok | {res.latency_s:.2f}s | "
                  f"attempts {res.attempts}{' | cached' if res.cached else ''}")  # fmt: skip
            print(f"DESC: {text}")
            print("JSON:", json.dumps(res.features) if res.features else f"null ({res.error})")
    print(f"\n[llm] wrote {out} {feats.shape}")
    print(json.dumps(cost, indent=2))


if __name__ == "__main__":
    main()
