"""Embed every `desc` in the processed data and save a per-loan matrix.

    python -m scripts.embed --config configs/e1.yaml
    python -m scripts.embed --config configs/e1.yaml --device cuda --batch-size 256   # Kaggle T4

Writes data/processed/embeddings/<model>.parquet (id + emb_000..) and
reports/runs/embed_<model>/cost.json (device, throughput, tokens; for the cost table).
Vectors are cached under cache/embeddings/<model>/, so reruns are free.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.features.embeddings import EmbedSettings, embed_texts, embeddings_path, save_embeddings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/e1.yaml")
    ap.add_argument("--device", default=None, help="cuda / mps / cpu (default: auto)")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None, help="embed only the first N loans")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ecfg = cfg["embeddings"]
    s = EmbedSettings(
        model_name=ecfg["model_name"],
        max_seq_length=ecfg["max_seq_length"],
        prefix=ecfg["prefix"],
        normalize=ecfg["normalize"],
        batch_size=args.batch_size or ecfg["batch_size"],
    )
    processed = Path(cfg["paths"]["processed"])
    df = pd.read_parquet(processed, columns=["id", "desc"])
    if args.limit:
        df = df.head(args.limit)

    cache_dir = Path(cfg["paths"]["cache_dir"]) / "embeddings" / s.slug
    matrix, stats = embed_texts(df["desc"], s, cache_dir, args.device, ecfg["fp16"])

    out = embeddings_path(processed.parent, s)
    if args.limit:
        out = out.with_name(f"{out.stem}.limit{args.limit}.parquet")
    save_embeddings(out, df["id"], matrix)

    cost_dir = Path(cfg["paths"]["reports_dir"]) / "runs" / f"embed_{s.slug}"
    cost_dir.mkdir(parents=True, exist_ok=True)
    cost = {**asdict(s), **asdict(stats), "texts_per_second": stats.texts_per_second}
    if stats.n_computed:  # a fully cached rerun says nothing about speed; keep the old file
        (cost_dir / "cost.json").write_text(json.dumps(cost, indent=2))
    print(f"[embed] wrote {out} {matrix.shape}")
    print(json.dumps(cost, indent=2))


if __name__ == "__main__":
    main()
