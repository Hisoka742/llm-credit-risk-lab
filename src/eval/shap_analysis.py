"""SHAP analysis via CatBoost's exact TreeSHAP (`ShapValues`), with no dependency on `shap`."""

from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool


def shap_values(
    model: CatBoostClassifier, X: pd.DataFrame, cat_cols: list[str], max_rows: int, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (SHAP in log-odds per feature, the X rows used). Subsamples to `max_rows`."""
    if len(X) > max_rows:
        X = X.sample(max_rows, random_state=seed)
    sv = model.get_feature_importance(Pool(X, cat_features=cat_cols), type="ShapValues")
    return pd.DataFrame(sv[:, :-1], columns=X.columns, index=X.index), X  # last col = bias


def importance_table(shap: pd.DataFrame) -> pd.DataFrame:
    imp = shap.abs().mean().sort_values(ascending=False)
    return pd.DataFrame(
        {"mean_abs_shap": imp, "rank": np.arange(1, len(imp) + 1), "share": imp / imp.sum()}
    )


def _fmt_value(v: object) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "missing"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))  # 3.0 -> "3" for 0-3 scales and 0/1 flags
    return str(v)


def by_value_table(shap: pd.DataFrame, X: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Mean SHAP (log-odds) per observed value of each discrete feature.

    For LLM features with a handful of levels this is easier to read than a beeswarm: for
    example, "financial_stress=3 adds +0.2 log-odds of default on average".
    """
    rows = []
    for c in cols:
        values = X[c].map(_fmt_value)
        for v, idx in values.groupby(values).groups.items():
            rows.append({"feature": c, "value": str(v), "n": len(idx),
                         "mean_shap": float(shap.loc[idx, c].mean())})  # fmt: skip
    return pd.DataFrame(rows)
