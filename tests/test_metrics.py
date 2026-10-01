from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.eval import metrics as M


@pytest.fixture
def yp() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    p = rng.uniform(0.01, 0.6, 5000)
    y = (rng.uniform(size=5000) < p).astype(int)  # perfectly calibrated by construction
    return y, p


def test_gini_extremes() -> None:
    y = np.array([0, 0, 1, 1])
    assert M.gini(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert M.gini(y, np.array([0.9, 0.8, 0.2, 0.1])) == -1.0
    assert M.gini(y, np.full(4, 0.5)) == 0.0


def test_bootstrap_ci_contains_point_and_is_seeded(yp) -> None:
    y, p = yp
    r1 = M.bootstrap_ci(y, p, M.gini, 200, seed=1)
    r2 = M.bootstrap_ci(y, p, M.gini, 200, seed=1)
    assert r1 == r2
    assert r1["ci_low"] < r1["value"] < r1["ci_high"]


def test_paired_bootstrap_identical_models_is_zero(yp) -> None:
    y, p = yp
    r = M.paired_bootstrap_diff(y, p, p, M.gini, 100, seed=0)
    assert r["diff"] == r["ci_low"] == r["ci_high"] == 0.0


def test_paired_bootstrap_detects_better_model(yp) -> None:
    y, p = yp
    noisy = p + np.random.default_rng(1).normal(0, 0.3, len(p))
    r = M.paired_bootstrap_diff(y, p, noisy, M.gini, 200, seed=0)
    assert r["ci_low"] > 0 and r["p_value_one_sided"] < 0.01


def test_psi() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=20000)
    assert M.psi(a, rng.normal(size=20000)) < 0.01
    assert M.psi(a, rng.normal(1.0, 1, size=20000)) > 0.25


def test_brier_and_calibration(yp) -> None:
    y, p = yp
    assert M.brier(np.array([0, 1]), np.array([0.0, 1.0])) == 0.0
    assert M.brier_skill(y, p) > 0
    t = M.calibration_table(y, p, 10)
    assert len(t) == 10 and t["n"].sum() == len(y)
    # 500 loans per bin: SE of observed rate is up to ~0.022, so allow ~3.5 SE
    assert np.allclose(t["mean_pred"], t["observed"], atol=0.08)


def test_gini_by_period_small_periods_get_no_gini(yp) -> None:
    y, p = yp
    period = pd.Series(["A"] * 4990 + ["B"] * 10)
    t = M.gini_by_period(y, p, period, 50, seed=0, min_n=500).set_index("period")
    assert np.isfinite(t.loc["A", "gini"]) and np.isnan(t.loc["B", "gini"])
