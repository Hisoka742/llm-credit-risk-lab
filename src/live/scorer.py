"""Live scoring: read a description with an LLM at request time and score it with the E2 model.

The demo answers one question: for a fixed borrower (a real test loan with all its tabular
features), how does the predicted PD move when only the *words* change?

What is honest to claim here, and what is not:
- The tabular features, the trained E2 model and the encoding are exactly those of the study.
- The reader is whatever backend is configured (GigaChat by default). The model was trained on
  labels from Qwen2.5-7B, so a different reader is a different annotator: the PD change is an
  illustration of the mechanism, not a validated prediction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool

from src.features.assemble import encode_llm
from src.features.llm_extract import FIELDS, DiskCache, ExtractResult, LLMSettings, extract_one


@dataclass
class Bundle:
    """Everything the service needs, written by `scripts.build_live`."""

    model: CatBoostClassifier
    features: list[str]
    categorical: list[str]
    X: pd.DataFrame  # one row per demo profile, indexed by loan id, columns == features
    profiles: list[dict[str, Any]]
    trained_on: str  # the LLM whose labels the model was trained on

    @classmethod
    def load(cls, directory: Path) -> Bundle:
        meta = json.loads((directory / "bundle.json").read_text(encoding="utf-8"))
        model = CatBoostClassifier()
        model.load_model(str(directory / "model.cbm"))
        X = pd.read_parquet(directory / "profiles_X.parquet").set_index("id")
        return cls(
            model=model,
            features=meta["features"],
            categorical=meta["categorical"],
            X=X[meta["features"]],
            profiles=meta["profiles"],
            trained_on=meta["trained_on"],
        )


def score_rows(b: Bundle, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (PD per row, SHAP values per row and feature, in log-odds)."""
    pool = Pool(X[b.features], cat_features=b.categorical)
    pd_ = b.model.predict_proba(pool)[:, 1]
    shap = b.model.get_feature_importance(pool, type="ShapValues")[:, :-1]
    return pd_, shap


def with_reading(b: Bundle, profile_id: str, reading: dict[str, Any] | None) -> pd.DataFrame:
    """The profile's feature row with its LLM columns replaced by `reading` (None = null)."""
    row = b.X.loc[[profile_id]].copy()
    raw = pd.DataFrame([{f: (reading or {}).get(f) for f in FIELDS}], index=row.index)
    enc, _ = encode_llm(raw)
    for col in enc.columns:
        row[col] = enc[col].astype(row[col].dtype)
    return row


class LiveScorer:
    def __init__(self, bundle: Bundle, settings: LLMSettings, client: Any, cache_dir: Path) -> None:
        self.b = bundle
        self.s = settings
        self.client = client
        self.cache = DiskCache(cache_dir)
        self._ids = {p["id"] for p in bundle.profiles}

    def has_profile(self, profile_id: str) -> bool:
        return profile_id in self._ids

    def read(self, text: str) -> ExtractResult:
        return extract_one(text, self.s, self.client, self.cache)

    def analyze(self, profile_id: str, text: str) -> dict[str, Any]:
        res = self.read(text)
        row = with_reading(self.b, profile_id, res.features)
        both = pd.concat([self.b.X.loc[[profile_id]], row])
        pds, shap = score_rows(self.b, both)
        llm_cols = [c for c in self.b.features if c.startswith("llm_")]
        idx = [self.b.features.index(c) for c in llm_cols]
        return {
            "profile_id": profile_id,
            "reader": self.s.model,
            "trained_on": self.b.trained_on,
            "reading": res.features,
            "error": res.error,
            "attempts": res.attempts,
            "cached": res.cached,
            "latency_s": round(res.latency_s, 3),
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
            "pd_original_text": float(pds[0]),
            "pd_your_text": float(pds[1]),
            # Log-odds contribution of each LLM field for the new text: which extracted
            # fact pushed the PD up or down.
            "contributions": [
                {"field": c.removeprefix("llm_"), "log_odds": float(shap[1, i])}
                for c, i in zip(llm_cols, idx, strict=True)
            ],
        }
