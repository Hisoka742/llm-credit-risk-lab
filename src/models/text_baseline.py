"""E4: TF-IDF + logistic regression on `desc` alone, as a cheap text-only baseline.

It answers "how much default signal is in the words at all", independently of the tabular
features. The inverse regularization C is chosen on validation AUC. The vectorizer is fit on
train only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def fit_tfidf_logreg(
    text_train: pd.Series,
    y_train: pd.Series,
    text_val: pd.Series,
    y_val: pd.Series,
    params: dict[str, Any],
    seed: int,
) -> tuple[TfidfVectorizer, LogisticRegression, dict[str, Any]]:
    vec = TfidfVectorizer(
        ngram_range=tuple(params["ngram_range"]),
        min_df=params["min_df"],
        max_features=params["max_features"],
        sublinear_tf=True,
        strip_accents="unicode",
        lowercase=True,
    )
    Xtr = vec.fit_transform(text_train)
    Xva = vec.transform(text_val)
    val_auc: dict[float, float] = {}
    best: tuple[float, LogisticRegression] | None = None
    for C in params["C_grid"]:
        lr = LogisticRegression(C=C, max_iter=2000, solver="liblinear", random_state=seed)
        lr.fit(Xtr, y_train)
        auc = float(roc_auc_score(y_val, lr.predict_proba(Xva)[:, 1]))
        val_auc[C] = auc
        if best is None or auc > val_auc[best[0]]:
            best = (C, lr)
    assert best is not None
    info = {"C": best[0], "val_auc_by_C": val_auc, "vocab_size": len(vec.vocabulary_)}
    return vec, best[1], info


def predict_text(vec: TfidfVectorizer, lr: LogisticRegression, text: pd.Series) -> np.ndarray:
    return lr.predict_proba(vec.transform(text))[:, 1]


def top_terms(vec: TfidfVectorizer, lr: LogisticRegression, k: int = 25) -> pd.DataFrame:
    """Terms with the largest positive (default-increasing) and negative coefficients."""
    coef = pd.Series(lr.coef_[0], index=vec.get_feature_names_out())
    top = pd.concat([coef.nlargest(k), coef.nsmallest(k)])
    return top.rename("coef").rename_axis("term").reset_index()
