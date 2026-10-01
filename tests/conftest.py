from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
REAL_RAW = REPO / "data" / "raw" / "accepted_2007_to_2018Q4.csv"
REAL_PROCESSED = REPO / "data" / "processed" / "loans.parquet"

STATUSES = [
    "Fully Paid",
    "Charged Off",
    "Current",
    "Late (31-120 days)",
    "Does not meet the credit policy. Status:Fully Paid",
    "Does not meet the credit policy. Status:Charged Off",
]
DESCS = [
    "  Borrower added on 08/18/12 > Consolidating credit cards.<br>",
    "547198 added on 10/19/09 > Paying off a car &amp; a card.<br/>",
    "<br>",
    None,
    "Balance went from < 40% to > 80% of my limit.",
]


@pytest.fixture
def synthetic_raw(tmp_path: Path) -> Path:
    """Small raw CSV shaped like the real file: leakage columns, an unreviewed column and
    the two footer rows."""
    rng = np.random.default_rng(0)
    n = 600
    months = pd.date_range("2010-01-01", periods=36, freq="MS")
    df = pd.DataFrame(
        {
            "id": np.arange(1000, 1000 + n).astype(str),
            "member_id": "",
            "loan_amnt": rng.integers(1000, 35000, n),
            "funded_amnt_inv": rng.integers(1000, 35000, n),
            "term": " 36 months",
            "int_rate": rng.uniform(5, 25, n).round(2),
            "grade": rng.choice(list("ABCDEFG"), n),
            "emp_title": "Teacher",
            "issue_d": pd.DatetimeIndex(rng.choice(months, n)).strftime("%b-%Y"),
            "loan_status": rng.choice(STATUSES, n),
            "pymnt_plan": "n",
            "url": "https://example/loan",
            "desc": rng.choice(np.array(DESCS, dtype=object), n),
            "title": "Debt consolidation",
            "earliest_cr_line": "Aug-2003",
            "revol_util": rng.uniform(0, 100, n).round(1),
            "total_pymnt": rng.uniform(0, 40000, n),
            "total_rec_prncp": rng.uniform(0, 40000, n),
            "recoveries": 0.0,
            "last_pymnt_d": "Jan-2016",
            "last_fico_range_high": 700,
            "out_prncp": 0.0,
            "hardship_flag": "N",
            "deferral_term": "",
            "debt_settlement_flag": "N",
            "settlement_status": "",
            "brand_new_column": 1,
        }
    )
    path = tmp_path / "accepted_2007_to_2018Q4.csv"
    df.to_csv(path, index=False)
    with path.open("a", encoding="utf-8") as f:
        pad = "," * (df.shape[1] - 1)
        f.write(f"Total amount funded in policy code 1: 1465324575{pad}\n")
        f.write(f"Total amount funded in policy code 2: 521953170{pad}\n")
    return path
