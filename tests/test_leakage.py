"""Fails if any post-origination column can survive into the processed data / feature matrix."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.load import read_header
from src.data.prepare import prepare
from src.features.leakage import (
    LEAKAGE_COLUMNS,
    PRE_ORIGINATION_COLUMNS,
    UNINFORMATIVE_COLUMNS,
    assert_no_leakage,
    find_leakage,
    is_leakage,
    partition_columns,
)
from tests.conftest import REAL_PROCESSED, REAL_RAW

# Every column CLAUDE.md names explicitly, plus representatives of each wildcard family.
SPEC_LEAKAGE = [
    "total_pymnt", "total_pymnt_inv", "total_rec_prncp", "total_rec_int", "total_rec_late_fee",
    "recoveries", "collection_recovery_fee", "last_pymnt_d", "last_pymnt_amnt", "next_pymnt_d",
    "out_prncp", "out_prncp_inv", "last_credit_pull_d", "last_fico_range_high",
    "last_fico_range_low", "hardship_flag", "hardship_amount", "settlement_status",
    "settlement_amount", "debt_settlement_flag", "funded_amnt_inv", "pymnt_plan", "loan_status",
]  # fmt: skip


@pytest.mark.parametrize("col", SPEC_LEAKAGE)
def test_spec_columns_are_flagged(col: str) -> None:
    assert is_leakage(col)


def test_allowlist_contains_no_leakage() -> None:
    assert find_leakage(PRE_ORIGINATION_COLUMNS) == []
    assert not (UNINFORMATIVE_COLUMNS & PRE_ORIGINATION_COLUMNS)


def test_assert_no_leakage_raises() -> None:
    with pytest.raises(ValueError, match="recoveries"):
        assert_no_leakage(["loan_amnt", "recoveries"])
    assert_no_leakage(["loan_amnt", "int_rate"])


def test_pipeline_output_has_no_leakage(synthetic_raw) -> None:
    res = prepare(synthetic_raw, chunksize=100, min_desc_chars=1, train_frac=0.7, val_frac=0.15)
    assert find_leakage(res.df.columns) == []
    assert "brand_new_column" not in res.df.columns  # unreviewed -> dropped, not kept
    assert res.dropped_unreviewed == ["brand_new_column"]
    assert {"member_id", "url"}.isdisjoint(res.df.columns)
    assert set(res.df.columns) <= PRE_ORIGINATION_COLUMNS | {"target", "split"}


@pytest.mark.skipif(not REAL_RAW.exists(), reason="raw Lending Club file not downloaded")
def test_every_real_column_is_reviewed() -> None:
    """Each raw column must be explicitly classified: a new column fails here, not silently."""
    _, leak, unknown = partition_columns(read_header(REAL_RAW))
    assert unknown == []
    assert set(leak) >= {c for c in LEAKAGE_COLUMNS}


@pytest.mark.skipif(not REAL_PROCESSED.exists(), reason="run scripts.prepare_data first")
def test_processed_parquet_has_no_leakage() -> None:
    cols = pd.read_parquet(REAL_PROCESSED, columns=None).columns
    assert_no_leakage(cols)


@pytest.mark.skipif(not REAL_PROCESSED.exists(), reason="run scripts.prepare_data first")
def test_tabular_feature_matrix_has_no_leakage() -> None:
    from src.features.tabular import build_tabular

    X, _ = build_tabular(pd.read_parquet(REAL_PROCESSED))
    assert_no_leakage(X.columns)
    assert not {"target", "split", "id", "issue_d", "desc"} & set(X.columns)
