from __future__ import annotations

import pandas as pd
import pytest

from src.data.clean import clean_desc, parse_month
from src.data.prepare import prepare
from src.data.split import SPLITS, assign_split, compute_boundaries
from src.data.target import make_target


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Borrower added on 08/18/12 > Consolidating cards.<br>", "Consolidating cards."),
        ("547198 added on 10/19/09 > Car &amp; card.<br/> Borrower added on 1/2/2010 > Thx",
         "Car & card. Thx"),
        ("<br>", ""),
        ("<br/>  <BR />", ""),
        (None, ""),
        (float("nan"), ""),
        ("from < 40% to > 80% of limit", "from < 40% to > 80% of limit"),
        ("<p>Hello <b>world</b></p>", "Hello world"),
    ],
)  # fmt: skip
def test_clean_desc(raw, expected) -> None:
    assert clean_desc(raw) == expected


def test_target_mapping() -> None:
    s = pd.Series(
        ["Fully Paid", "Charged Off", "Default", "Current", "In Grace Period",
         "Late (16-30 days)", "Does not meet the credit policy. Status:Charged Off",
         "Does not meet the credit policy. Status:Fully Paid", None]
    )  # fmt: skip
    assert make_target(s).tolist() == [0, 1, 1, pd.NA, pd.NA, pd.NA, 1, 0, pd.NA]


def test_parse_month_both_formats() -> None:
    out = parse_month(pd.Series(["Dec-2015", "Dec-15", "Total amount funded", None]))
    assert out.iloc[0] == out.iloc[1] == pd.Timestamp("2015-12-01")
    assert out.iloc[2:].isna().all()


def test_split_is_time_ordered_and_month_disjoint() -> None:
    dates = pd.Series(pd.date_range("2010-01-01", "2014-12-31", freq="D"))
    b = compute_boundaries(dates, 0.7, 0.15)
    split = assign_split(dates, b)
    by = {s: dates[split == s] for s in SPLITS}
    assert by["train"].max() < by["val"].min()
    assert by["val"].max() < by["test"].min()
    months = {s: set(d.dt.to_period("M")) for s, d in by.items()}
    assert not (months["train"] & months["val"] or months["val"] & months["test"])
    shares = split.value_counts(normalize=True)
    assert abs(shares["train"] - 0.70) < 0.02 and abs(shares["val"] - 0.15) < 0.02


def test_prepare_end_to_end(synthetic_raw) -> None:
    res = prepare(synthetic_raw, chunksize=100, min_desc_chars=1, train_frac=0.7, val_frac=0.15)
    funnel = dict(res.funnel)
    assert funnel["raw rows"] == 602  # 600 loans + 2 footer rows
    assert funnel["valid issue_d"] == 600
    df = res.df
    assert set(df["target"].unique()) <= {0, 1}
    assert (df["desc"].str.len() > 0).all()
    assert not df["desc"].str.contains("added on|<br", regex=True).any()
    assert df["issue_d"].is_monotonic_increasing
    assert res.coverage["n_loans"].sum() == 600
    assert res.splits["rows"].sum() == len(df)
