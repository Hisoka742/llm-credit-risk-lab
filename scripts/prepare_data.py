"""Build data/processed/loans.parquet from the raw Lending Club CSV.

python -m scripts.prepare_data --config configs/base.yaml
python -m scripts.prepare_data --nrows 200000        # quick smoke run
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.data.load import find_raw_file
from src.data.prepare import prepare


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/base.yaml")
    ap.add_argument("--raw", default=None, help="override path to the raw CSV")
    ap.add_argument("--nrows", type=int, default=None, help="read only the first N raw rows")
    args = ap.parse_args()

    cfg = load_config(args.config)
    paths, dcfg, scfg = cfg["paths"], cfg["data"], cfg["split"]
    raw = find_raw_file(paths["raw_dir"], dcfg["raw_glob"], args.raw or paths.get("raw_file"))
    print(f"Reading {raw}" + (f" (first {args.nrows:,} rows)" if args.nrows else ""))

    t0 = time.perf_counter()
    res = prepare(
        raw,
        chunksize=dcfg["chunksize"],
        min_desc_chars=dcfg["min_desc_chars"],
        train_frac=scfg["train_frac"],
        val_frac=scfg["val_frac"],
        nrows=args.nrows,
    )

    pd.set_option("display.width", 160)
    print(f"\nDropped {len(res.dropped_leakage)} leakage columns.")
    if res.dropped_unreviewed:
        print(
            f"WARNING: dropped unreviewed columns, classify them in leakage.py: "
            f"{res.dropped_unreviewed}"
        )

    print("\n== Rows after each filter step ==")
    prev = None
    for step, n in res.funnel:
        kept = "" if prev is None else f"  ({n / prev:6.1%} of previous)"
        print(f"  {step:<50} {n:>10,}{kept}")
        prev = n

    print("\n== desc coverage by issue year (before desc filter) ==")
    cov = res.coverage.copy()
    for c in ("coverage_all", "coverage_finished", "default_rate_with_desc"):
        cov[c] = cov[c].map(lambda v: "" if pd.isna(v) else f"{v:.1%}")
    print(cov.to_string())

    print("\n== Out-of-time split ==")
    sp = res.splits.copy()
    sp["share"] = sp["share"].map("{:.1%}".format)
    sp["default_rate"] = sp["default_rate"].map("{:.2%}".format)
    print(sp.to_string())

    out = Path(paths["processed"])
    out.parent.mkdir(parents=True, exist_ok=True)
    res.df.to_parquet(out, index=False)
    summary_path = Path(paths["reports_dir"]) / "data" / "prepare_data.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"raw_file": str(raw), "nrows_limit": args.nrows, **res.to_dict()}
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out} {res.df.shape} and {summary_path} in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
