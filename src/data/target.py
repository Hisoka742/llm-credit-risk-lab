"""Binary default target from `loan_status`.

Only finished outcomes are labeled. Current / Late / In Grace Period loans are still running,
so labeling them "good" would understate PD for recent vintages. They get <NA> and are dropped.

"Does not meet the credit policy. Status:Fully Paid" is labeled 0 even though CLAUDE.md lists
only plain "Fully Paid". These are 2007-2010 loans issued under an older policy. Keeping their
Charged Off rows as 1 while dropping their Fully Paid rows would keep only the bad outcomes of
that cohort and inflate its default rate.
"""

from __future__ import annotations

import pandas as pd

GOOD_STATUSES = frozenset({"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"})
BAD_STATUSES = frozenset(
    {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}
)


def make_target(status: pd.Series) -> pd.Series:
    """Map loan_status to 1 (default), 0 (paid off) or <NA> (unfinished / unknown)."""
    s = status.astype("string").str.strip()
    target = pd.Series(pd.NA, index=status.index, dtype="Int8")
    target[s.isin(BAD_STATUSES).fillna(False)] = 1
    target[s.isin(GOOD_STATUSES).fillna(False)] = 0
    return target
