"""Paired comparison of an experiment against a baseline run on the same test loans."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.eval import metrics as M


def load_predictions(runs_dir: Path, name: str) -> pd.DataFrame:
    path = runs_dir / name / "predictions.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run the {name} experiment first.")
    return pd.read_parquet(path)


def compare_to_baseline(
    new: pd.DataFrame,
    base: pd.DataFrame,
    n_boot: int,
    seed: int,
    ci: float,
    split: str = "test",
    min_period_n: int = 500,
) -> dict[str, Any]:
    """Paired bootstrap of Gini and Brier differences (new - base) on one split.

    The two prediction files are joined on loan id, and both targets must agree, so a
    changed dataset cannot be compared by accident.
    """
    a = new.loc[new["split"] == split, ["id", "issue_d", "target", "score"]]
    b = base.loc[base["split"] == split, ["id", "target", "score"]]
    m = a.merge(b, on="id", suffixes=("", "_base"), validate="one_to_one")
    if len(m) != len(a) or len(m) != len(b) or (m["target"] != m["target_base"]).any():
        raise ValueError("baseline and experiment were scored on different test loans")
    y, p, p0 = m["target"].to_numpy(), m["score"].to_numpy(), m["score_base"].to_numpy()

    by_q = []
    for q, g in m.groupby(m["issue_d"].dt.to_period("Q").astype(str)):
        if len(g) < min_period_n:
            continue
        r = M.paired_bootstrap_diff(
            g["target"].to_numpy(), g["score"].to_numpy(), g["score_base"].to_numpy(),
            M.gini, n_boot, seed, ci,
        )  # fmt: skip
        by_q.append({"period": q, "n": len(g), **r})

    return {
        "split": split,
        "n": len(m),
        "gini_base": M.gini(y, p0),
        "gini_new": M.gini(y, p),
        "gini_diff": M.paired_bootstrap_diff(y, p, p0, M.gini, n_boot, seed, ci),
        # Negative Brier diff = the new model is better.
        "brier_diff": M.paired_bootstrap_diff(y, p, p0, M.brier, n_boot, seed, ci),
        "gini_diff_by_quarter": by_q,
    }
