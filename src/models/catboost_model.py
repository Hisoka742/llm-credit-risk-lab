"""CatBoost training with early stopping on the validation split."""

from __future__ import annotations

from typing import Any

import pandas as pd
from catboost import CatBoostClassifier, Pool


def fit_catboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    cat_cols: list[str],
    params: dict[str, Any],
    seed: int,
) -> CatBoostClassifier:
    """Fit on train, choose the iteration count by val AUC. Test is never touched here.

    No class weights: PD needs calibrated probabilities, and a ~15% default rate is not
    imbalanced enough to need reweighting for ranking.
    """
    model = CatBoostClassifier(
        loss_function="Logloss",
        random_seed=seed,
        use_best_model=True,
        allow_writing_files=False,
        verbose=250,
        **params,
    )
    model.fit(
        Pool(X_train, y_train, cat_features=cat_cols),
        eval_set=Pool(X_val, y_val, cat_features=cat_cols),
    )
    return model


def predict_pd(model: CatBoostClassifier, X: pd.DataFrame, cat_cols: list[str]) -> pd.Series:
    return pd.Series(
        model.predict_proba(Pool(X, cat_features=cat_cols))[:, 1], index=X.index, name="score"
    )
