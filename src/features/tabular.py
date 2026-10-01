"""Tabular feature matrix for all experiments (the E0 baseline and the tabular half of E1-E3).

Starts from the processed parquet, which only holds allowlisted pre-origination columns
(see leakage.py), and removes columns that are not tabular model inputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.leakage import assert_no_leakage

# Columns in the processed data that are deliberately not tabular features.
EXCLUDED: dict[str, str] = {
    "id": "identifier",
    "issue_d": "split key. A time feature would let the model learn vintage default rates "
    "that cannot extrapolate to out-of-time loans",
    "target": "label",
    "split": "split assignment",
    "desc": "free text, used by the text experiments (E1-E4)",
    "title": "free text typed by the borrower (text field per CLAUDE.md)",
    "emp_title": "free text typed by the borrower (text field per CLAUDE.md)",
    "zip_code": "3-digit zip is a known fair-lending (redlining) proxy, and has ~900 levels",
    "earliest_cr_line": "raw date, replaced by credit_history_months",
    "sec_app_earliest_cr_line": "raw date, all-missing before 2017",
}

CATEGORICAL: tuple[str, ...] = (
    "term",
    "grade",
    "sub_grade",
    "emp_length",
    "home_ownership",
    "verification_status",
    "purpose",
    "addr_state",
    "initial_list_status",
    "application_type",
    "verification_status_joint",
    "disbursement_method",
)
MISSING_CAT = "__NA__"


def _months_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    return (later.dt.year - earlier.dt.year) * 12 + (later.dt.month - earlier.dt.month)


def build_tabular(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (X, categorical column names). Rows align with `df`."""
    X = df.drop(columns=[c for c in EXCLUDED if c in df.columns])

    # A few standard ratios. GBDTs can approximate ratios, but only coarsely with depth 6.
    income = df["annual_inc"].where(df["annual_inc"] > 0)
    X["credit_history_months"] = _months_between(df["issue_d"], df["earliest_cr_line"])
    X["fico_mid"] = (df["fico_range_low"] + df["fico_range_high"]) / 2
    X["loan_to_income"] = df["loan_amnt"] / income
    X["installment_to_monthly_income"] = df["installment"] / (income / 12)
    X = X.drop(columns=["fico_range_high"])  # fico_range_low + 4 in practice, redundant

    cat_cols = [c for c in CATEGORICAL if c in X.columns]
    for c in cat_cols:
        X[c] = X[c].astype(object).where(X[c].notna(), MISSING_CAT).astype(str)
    num_cols = [c for c in X.columns if c not in cat_cols]
    X[num_cols] = X[num_cols].astype("float64").replace([np.inf, -np.inf], np.nan)
    assert_no_leakage(X.columns)
    return X, cat_cols


def informative_columns(X_train: pd.DataFrame) -> list[str]:
    """Columns with at least two distinct non-missing values *in train*.

    Many bureau fields (open_acc_6m, il_util, sec_app_*, ...) were only reported from
    2015-2017, so they are entirely missing in this pre-2014 text sample. They are dropped
    using train only, so the decision cannot depend on val/test.
    """
    return [c for c in X_train.columns if X_train[c].nunique(dropna=True) > 1]
