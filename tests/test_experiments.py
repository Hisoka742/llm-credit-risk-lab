from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from catboost import CatBoostClassifier, Pool

from src.eval.shap_analysis import by_value_table, importance_table, shap_values
from src.features.assemble import load_llm_features
from src.features.leakage import assert_no_leakage
from src.features.llm_extract import FIELDS
from src.models.text_baseline import fit_tfidf_logreg, predict_text, top_terms


def _llm_file(tmp_path, ids, ok=True):
    rows = []
    for i in ids:
        row = {
            "loan_purpose_category": "credit_card", "financial_stress": 2,
            "employment_stability": 0, "mentions_other_debts": True,
            "mentions_job_loss_or_income_drop": False,
            "mentions_medical_or_family_emergency": False, "has_repayment_plan": True,
            "text_quality": 3,
        }  # fmt: skip
        if not ok:
            row = dict.fromkeys(FIELDS)
        rows.append({"id": i, **row, "llm_ok": ok, "llm_attempts": 1, "llm_error": None})
    path = tmp_path / "llm.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def test_load_llm_features_types_and_order(tmp_path) -> None:
    path = _llm_file(tmp_path, ["a", "b", "c"])
    X, cats, null_rate = load_llm_features(path, pd.Series(["c", "a"]))
    assert list(X.columns) == [f"llm_{f}" for f in FIELDS]
    assert cats == ["llm_loan_purpose_category", "llm_employment_stability"]
    assert X["llm_employment_stability"].tolist() == ["0", "0"]  # categorical, not ordinal
    assert X["llm_financial_stress"].dtype == "float64"
    assert X["llm_mentions_other_debts"].tolist() == [1.0, 1.0]
    assert null_rate == 0.0
    assert_no_leakage(X.columns)


def test_load_llm_features_nulls_and_missing_loans(tmp_path) -> None:
    X, _, null_rate = load_llm_features(_llm_file(tmp_path, ["a"], ok=False), pd.Series(["a"]))
    assert null_rate == 1.0
    assert X["llm_financial_stress"].isna().all()
    assert X["llm_loan_purpose_category"].tolist() == ["__NA__"]
    with pytest.raises(ValueError, match="no LLM extraction"):
        load_llm_features(_llm_file(tmp_path, ["a"]), pd.Series(["a", "zzz"]))


def test_shap_tables_sum_to_prediction() -> None:
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"x": rng.normal(size=400), "llm_s": rng.integers(0, 4, 400).astype(float),
                      "cat": rng.choice(["a", "b"], 400)})  # fmt: skip
    y = (X["x"] + X["llm_s"] + rng.normal(size=400) > 1.5).astype(int)
    m = CatBoostClassifier(iterations=50, verbose=0, random_seed=0, allow_writing_files=False)
    m.fit(Pool(X, y, cat_features=["cat"]))
    sv, Xs = shap_values(m, X, ["cat"], max_rows=300, seed=0)
    assert sv.shape == (300, 3)
    raw = m.predict(Pool(Xs, cat_features=["cat"]), prediction_type="RawFormulaVal")
    bias = m.get_feature_importance(Pool(Xs, cat_features=["cat"]), type="ShapValues")[:, -1]
    assert np.allclose(sv.sum(axis=1) + bias, raw, atol=1e-6)  # SHAP additivity
    tab = importance_table(sv)
    assert tab["share"].sum() == pytest.approx(1.0)
    bv = by_value_table(sv, Xs, ["llm_s"]).set_index("value")
    assert bv.loc["3", "mean_shap"] > bv.loc["0", "mean_shap"]  # higher stress, higher PD


def test_tfidf_baseline_learns_signal() -> None:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 600)
    text = pd.Series(["need help with bills" if t else "consolidate cards lower rate"
                      for t in y])  # fmt: skip
    params = {"ngram_range": [1, 2], "min_df": 1, "max_features": 1000, "C_grid": [0.1, 1.0]}
    vec, lr, info = fit_tfidf_logreg(text[:400], y[:400], text[400:], y[400:], params, 0)
    assert info["val_auc_by_C"][info["C"]] == max(info["val_auc_by_C"].values())
    assert (predict_text(vec, lr, text[400:])[y[400:] == 1] > 0.5).all()
    terms = top_terms(vec, lr, k=3)
    assert terms.iloc[0]["coef"] > 0 > terms.iloc[-1]["coef"]
