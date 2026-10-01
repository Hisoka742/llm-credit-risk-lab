"""Out-of-time train/val/test split on issue month.

Boundaries snap to whole months, so no issue month appears in two splits. Each boundary is
placed at the month edge whose cumulative row share is closest to the target fraction, so
the realized fractions are near 70/15/15 but not exact. The realized shares are reported.

Known limitation (standard for out-of-time PD validation): outcome windows overlap. A 2011
train loan can default in 2013, after some test loans were issued. Features are all known at
origination, so this is not feature leakage, but the train labels do reflect macro conditions
from the test period.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class SplitBoundaries:
    train_end: pd.Timestamp  # last issue month in train (inclusive)
    val_end: pd.Timestamp  # last issue month in val (inclusive); test is everything after


def compute_boundaries(dates: pd.Series, train_frac: float, val_frac: float) -> SplitBoundaries:
    if not (0 < train_frac < 1 and 0 < val_frac < 1 and train_frac + val_frac < 1):
        raise ValueError("need 0 < train_frac, val_frac and train_frac + val_frac < 1")
    months = dates.dt.to_period("M")
    counts = months.value_counts().sort_index()
    if len(counts) < 3:
        raise ValueError(f"need >= 3 distinct issue months, got {len(counts)}")
    cum = (counts.cumsum() / counts.sum()).to_numpy()

    # Candidate cut after month i. The train cut is limited to months 0..n-3 so that val and
    # test each keep at least one month.
    n = len(counts)
    i_train = int(np.argmin(np.abs(cum[: n - 2] - train_frac)))
    j_range = np.arange(i_train + 1, n - 1)
    i_val = int(j_range[np.argmin(np.abs(cum[j_range] - (train_frac + val_frac)))])
    return SplitBoundaries(
        train_end=counts.index[i_train].to_timestamp(),
        val_end=counts.index[i_val].to_timestamp(),
    )


def assign_split(dates: pd.Series, b: SplitBoundaries) -> pd.Series:
    month = dates.dt.to_period("M").dt.to_timestamp()
    split = np.where(month <= b.train_end, "train", np.where(month <= b.val_end, "val", "test"))
    return pd.Series(pd.Categorical(split, categories=SPLITS), index=dates.index, name="split")
