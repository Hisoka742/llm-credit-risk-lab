"""Build the feature matrix for an experiment from its `feature_sets`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.features.embeddings import (
    EmbedSettings,
    embeddings_path,
    fit_reducer,
    load_embeddings,
    reduce,
)
from src.features.leakage import assert_no_leakage
from src.features.llm_extract import FIELDS as LLM_FIELDS
from src.features.llm_extract import LLMSettings
from src.features.tabular import MISSING_CAT, build_tabular, informative_columns

IMPLEMENTED = {"tabular", "embeddings", "llm"}
# employment_stability 0 means "not mentioned", not "least stable", so it is not ordinal.
LLM_CATEGORICAL = ("loan_purpose_category", "employment_stability")


def llm_features_path(processed_dir: Path, model: str) -> Path:
    return processed_dir / "llm_features" / f"{LLMSettings(model=model).slug}.parquet"


def load_llm_features(path: Path, ids: pd.Series) -> tuple[pd.DataFrame, list[str], float]:
    """LLM features aligned to `ids`, prefixed `llm_`. Returns (frame, categorical, null rate).

    Every loan must have an extraction row. A null result (invalid JSON twice) is allowed
    and becomes NaN / __NA__. A loan that was never sent to the LLM is an error, so a
    partial extraction run cannot silently give mostly-missing features.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run: python -m scripts.llm_extract --config ...")
    llm = pd.read_parquet(path).drop_duplicates("id").set_index("id")
    missing = ~ids.isin(llm.index)
    if missing.any():
        raise ValueError(
            f"{int(missing.sum()):,} loans have no LLM extraction. Run scripts.llm_extract on "
            "the full sample, or pass --llm-sample to restrict the experiment to it."
        )
    llm = llm.loc[ids.to_numpy(), LLM_FIELDS + ["llm_ok"]].reset_index(drop=True)
    null_rate = float(1 - llm.pop("llm_ok").astype(bool).mean())
    out = pd.DataFrame(index=llm.index)
    cats = []
    for f in LLM_FIELDS:
        col = f"llm_{f}"
        if f in LLM_CATEGORICAL:
            out[col] = llm[f].astype(object).where(llm[f].notna(), MISSING_CAT).astype(str)
            out[col] = out[col].str.replace(r"\.0$", "", regex=True)  # 2.0 -> "2" after NaN upcast
            cats.append(col)
        else:
            out[col] = pd.to_numeric(llm[f].astype(object), errors="coerce").astype("float64")
    return out, cats, null_rate


def assemble_features(
    cfg: dict[str, Any], df: pd.DataFrame, is_train: np.ndarray
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    """Return (X, categorical columns, info). Anything fitted uses train rows only."""
    sets = cfg["experiment"]["feature_sets"]
    if unknown := set(sets) - IMPLEMENTED:
        raise NotImplementedError(f"feature sets {sorted(unknown)} not implemented yet")
    info: dict[str, Any] = {}

    X, cat_cols = build_tabular(df)
    keep = informative_columns(X[is_train])
    info["dropped_constant_in_train"] = sorted(set(X.columns) - set(keep))
    X, cat_cols = X[keep], [c for c in cat_cols if c in keep]

    if "embeddings" in sets:
        ecfg = cfg["embeddings"]
        s = EmbedSettings(ecfg["model_name"], ecfg["max_seq_length"], ecfg["prefix"])
        path = embeddings_path(Path(cfg["paths"]["processed"]).parent, s)
        E = load_embeddings(path, df["id"])
        pca = fit_reducer(E[is_train], ecfg["n_components"], cfg["seed"])
        Z = reduce(pca, E)
        Z.index = X.index
        X = pd.concat([X, Z], axis=1)
        info["embeddings"] = {
            "model": s.model_name,
            "dim": int(E.shape[1]),
            "n_components": int(pca.n_components_),
            "explained_variance_ratio_total": float(pca.explained_variance_ratio_.sum()),
        }

    if "llm" in sets:
        model = cfg["llm"]["model"]
        L, llm_cats, null_rate = load_llm_features(
            llm_features_path(Path(cfg["paths"]["processed"]).parent, model), df["id"]
        )
        L.index = X.index
        X = pd.concat([X, L], axis=1)
        cat_cols = cat_cols + llm_cats
        info["llm"] = {"model": model, "n_features": L.shape[1], "null_rate": null_rate}

    assert_no_leakage(X.columns)
    return X, cat_cols, info
