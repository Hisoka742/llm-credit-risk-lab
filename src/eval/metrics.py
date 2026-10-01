"""Discrimination, calibration and stability metrics with bootstrap confidence intervals."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

Metric = Callable[[np.ndarray, np.ndarray], float]


def auc(y: np.ndarray, p: np.ndarray) -> float:
    return float(roc_auc_score(y, p))


def gini(y: np.ndarray, p: np.ndarray) -> float:
    return 2 * auc(y, p) - 1


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def brier_skill(y: np.ndarray, p: np.ndarray) -> float:
    """1 - Brier / Brier of always predicting the observed rate. 0 = no better than the rate."""
    y = np.asarray(y)
    return 1 - brier(y, p) / brier(y, np.full(len(y), y.mean()))


def _bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def bootstrap_ci(
    y: np.ndarray, p: np.ndarray, metric: Metric, n_boot: int, seed: int, ci: float = 0.95
) -> dict[str, float]:
    """Percentile bootstrap over loans. Draws with a single class are skipped (tiny n only)."""
    y, p = np.asarray(y), np.asarray(p)
    stats = [
        metric(y[i], p[i])
        for i in _bootstrap_indices(len(y), n_boot, seed)
        if 0 < y[i].sum() < len(i)
    ]
    a = (1 - ci) / 2
    return {
        "value": metric(y, p),
        "ci_low": float(np.quantile(stats, a)),
        "ci_high": float(np.quantile(stats, 1 - a)),
        "n_boot": len(stats),
    }


def paired_bootstrap_diff(
    y: np.ndarray,
    p_new: np.ndarray,
    p_base: np.ndarray,
    metric: Metric,
    n_boot: int,
    seed: int,
    ci: float = 0.95,
) -> dict[str, float]:
    """metric(new) - metric(base), resampling the *same* loans for both models.

    Pairing removes the shared sampling noise, so the CI on the difference is much narrower
    than comparing two independent CIs. p_value is the one-sided share of draws with diff <= 0.
    """
    y, p_new, p_base = map(np.asarray, (y, p_new, p_base))
    diffs = np.array(
        [
            metric(y[i], p_new[i]) - metric(y[i], p_base[i])
            for i in _bootstrap_indices(len(y), n_boot, seed)
            if 0 < y[i].sum() < len(i)
        ]
    )
    a = (1 - ci) / 2
    return {
        "diff": metric(y, p_new) - metric(y, p_base),
        "ci_low": float(np.quantile(diffs, a)),
        "ci_high": float(np.quantile(diffs, 1 - a)),
        "p_value_one_sided": float(np.mean(diffs <= 0)),
        "n_boot": len(diffs),
    }


def calibration_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Observed vs mean predicted default rate per score decile (equal-count bins)."""
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    df["bin"] = pd.qcut(df["p"], n_bins, labels=False, duplicates="drop")
    g = df.groupby("bin")
    return pd.DataFrame(
        {"n": g.size(), "mean_pred": g["p"].mean(), "observed": g["y"].mean()}
    ).reset_index(drop=True)


def psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index of `actual` vs `expected`, on decile bins of `expected`.

    Rule of thumb in credit risk: < 0.10 stable, 0.10-0.25 moderate shift, > 0.25 major shift.
    """
    expected, actual = np.asarray(expected), np.asarray(actual)
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, n_bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, eps, None), np.clip(a, eps, None)
    return float(np.sum((a - e) * np.log(a / e)))


def gini_by_period(
    y: np.ndarray,
    p: np.ndarray,
    period: pd.Series,
    n_boot: int,
    seed: int,
    ci: float = 0.95,
    min_n: int = 500,
) -> pd.DataFrame:
    """Gini with bootstrap CI per period. Periods below `min_n` loans get counts only."""
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p), "period": np.asarray(period)})
    rows = []
    for key, g in df.groupby("period", sort=True):
        row = {"period": str(key), "n": len(g), "defaults": int(g["y"].sum())}
        if len(g) >= min_n and 0 < row["defaults"] < len(g):
            r = bootstrap_ci(g["y"].to_numpy(), g["p"].to_numpy(), gini, n_boot, seed, ci)
            row.update(gini=r["value"], ci_low=r["ci_low"], ci_high=r["ci_high"])
        rows.append(row)
    return pd.DataFrame(rows)
