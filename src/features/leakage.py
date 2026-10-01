"""Leakage control for the Lending Club `accepted_2007_to_2018Q4` file.

A PD model is scored at application time, so every feature must be known *before* the loan
is issued. The raw file is a snapshot taken in 2019 and mixes origination attributes with
servicing history (payments, recoveries, hardship plans, settlements, refreshed FICO).
Those columns are near-perfect proxies of the outcome and must never reach a model.

Two lists, used together:
- `LEAKAGE_COLUMNS` / `LEAKAGE_PREFIXES`: denylist of post-origination columns, each with the
  reason it leaks.
- `PRE_ORIGINATION_COLUMNS`: allowlist of columns that were reviewed and judged to be known at
  application time.
The pipeline keeps only allowlisted columns. A column that is on neither list (for example
from a new data release) is dropped and reported, so an unreviewed column can never slip
into the features by accident.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

# Prefix families. `last_` is safe as a prefix because every `last_*` column is servicing
# data (last_pymnt_d, last_pymnt_amnt, last_credit_pull_d, last_fico_range_*). Fields like
# `mths_since_last_delinq` or `inq_last_6mths` do not *start* with `last_`.
LEAKAGE_PREFIXES: dict[str, str] = {
    "total_pymnt": "payments received to date",
    "total_rec_": "principal/interest/late fees received to date",
    "out_prncp": "outstanding principal at snapshot date",
    "last_": "last payment / last credit pull / refreshed FICO, all after issuance",
    "hardship_": "hardship plan, only exists for borrowers who got into trouble",
    "settlement_": "debt settlement after default",
    "debt_settlement_": "debt settlement after default",
}

LEAKAGE_COLUMNS: dict[str, str] = {
    # The label itself. Kept here so that any feature matrix containing it fails the check.
    "loan_status": "outcome label",
    # Payments / recoveries
    "total_pymnt": "payments received to date",
    "total_pymnt_inv": "payments received to date (investor share)",
    "total_rec_prncp": "principal received to date",
    "total_rec_int": "interest received to date",
    "total_rec_late_fee": "late fees received, only non-zero if the borrower was late",
    "recoveries": "post charge-off recoveries, non-zero only for defaults",
    "collection_recovery_fee": "post charge-off collection fee",
    "out_prncp": "outstanding principal at snapshot",
    "out_prncp_inv": "outstanding principal at snapshot (investor share)",
    "last_pymnt_d": "date of last payment",
    "last_pymnt_amnt": "amount of last payment",
    "next_pymnt_d": "next scheduled payment, empty once the loan is closed",
    "last_credit_pull_d": "date of most recent bureau pull (servicing)",
    "last_fico_range_high": "refreshed FICO after issuance, collapses on default",
    "last_fico_range_low": "refreshed FICO after issuance, collapses on default",
    # Funding / servicing state
    "funded_amnt_inv": "investor-funded amount, finalized after listing closes",
    "pymnt_plan": "payment plan flag set during servicing",
    # Hardship program (2017+), including columns that lack the hardship_ prefix
    "hardship_flag": "hardship program",
    "hardship_type": "hardship program",
    "hardship_reason": "hardship program",
    "hardship_status": "hardship program",
    "hardship_amount": "hardship program",
    "hardship_start_date": "hardship program",
    "hardship_end_date": "hardship program",
    "hardship_length": "hardship program",
    "hardship_dpd": "hardship program",
    "hardship_loan_status": "hardship program",
    "hardship_payoff_balance_amount": "hardship program",
    "hardship_last_payment_amount": "hardship program",
    "deferral_term": "hardship program (no prefix)",
    "payment_plan_start_date": "hardship program (no prefix)",
    "orig_projected_additional_accrued_interest": "hardship program (no prefix)",
    # Debt settlement
    "debt_settlement_flag": "debt settlement after default",
    "debt_settlement_flag_date": "debt settlement after default",
    "settlement_status": "debt settlement after default",
    "settlement_date": "debt settlement after default",
    "settlement_amount": "debt settlement after default",
    "settlement_percentage": "debt settlement after default",
    "settlement_term": "debt settlement after default",
}

# Reviewed as known at application/listing time. Notes on the less obvious ones:
# - grade/sub_grade/int_rate are the output of Lending Club's own risk model at origination.
#   They are legitimate (a bank has its own score at decision time) but make the baseline
#   strong, which raises the bar for text features. This is deliberate.
# - Bureau attributes (tot_cur_bal, mo_sin_*, num_*, ...) are documented as at application.
# - id/issue_d/desc/title/emp_title are kept for joins, splitting and text pipelines.
#   The tabular feature builder decides which of these become model inputs.
PRE_ORIGINATION_COLUMNS: frozenset[str] = frozenset(
    """
    id loan_amnt funded_amnt term int_rate installment grade sub_grade emp_title emp_length
    home_ownership annual_inc verification_status issue_d desc purpose title zip_code
    addr_state dti delinq_2yrs earliest_cr_line fico_range_low fico_range_high inq_last_6mths
    mths_since_last_delinq mths_since_last_record open_acc pub_rec revol_bal revol_util
    total_acc initial_list_status collections_12_mths_ex_med mths_since_last_major_derog
    policy_code application_type annual_inc_joint dti_joint verification_status_joint
    acc_now_delinq tot_coll_amt tot_cur_bal open_acc_6m open_act_il open_il_12m open_il_24m
    mths_since_rcnt_il total_bal_il il_util open_rv_12m open_rv_24m max_bal_bc all_util
    total_rev_hi_lim inq_fi total_cu_tl inq_last_12m acc_open_past_24mths avg_cur_bal
    bc_open_to_buy bc_util chargeoff_within_12_mths delinq_amnt mo_sin_old_il_acct
    mo_sin_old_rev_tl_op mo_sin_rcnt_rev_tl_op mo_sin_rcnt_tl mort_acc mths_since_recent_bc
    mths_since_recent_bc_dlq mths_since_recent_inq mths_since_recent_revol_delinq
    num_accts_ever_120_pd num_actv_bc_tl num_actv_rev_tl num_bc_sats num_bc_tl num_il_tl
    num_op_rev_tl num_rev_accts num_rev_tl_bal_gt_0 num_sats num_tl_120dpd_2m num_tl_30dpd
    num_tl_90g_dpd_24m num_tl_op_past_12m pct_tl_nvr_dlq percent_bc_gt_75
    pub_rec_bankruptcies tax_liens tot_hi_cred_lim total_bal_ex_mort total_bc_limit
    total_il_high_credit_limit revol_bal_joint sec_app_fico_range_low sec_app_fico_range_high
    sec_app_earliest_cr_line sec_app_inq_last_6mths sec_app_mort_acc sec_app_open_acc
    sec_app_revol_util sec_app_open_act_il sec_app_num_rev_accts
    sec_app_chargeoff_within_12_mths sec_app_collections_12_mths_ex_med
    sec_app_mths_since_last_major_derog disbursement_method
    """.split()
)

# Not leakage, but no information: member_id is empty in this release and url is just the id.
UNINFORMATIVE_COLUMNS: frozenset[str] = frozenset({"member_id", "url"})


def is_leakage(column: str) -> bool:
    return column in LEAKAGE_COLUMNS or column.startswith(tuple(LEAKAGE_PREFIXES))


def find_leakage(columns: Iterable[str]) -> list[str]:
    return [c for c in columns if is_leakage(c)]


def assert_no_leakage(columns: Iterable[str]) -> None:
    """Raise if any post-origination column is present. Call on every feature matrix."""
    leaked = find_leakage(columns)
    if leaked:
        raise ValueError(f"Leakage columns present: {leaked}")


def partition_columns(columns: Iterable[str]) -> tuple[list[str], list[str], list[str]]:
    """Split raw columns into (keep, leakage, unreviewed). Uninformative ones are in neither."""
    keep, leak, unknown = [], [], []
    for c in columns:
        if is_leakage(c):
            leak.append(c)
        elif c in PRE_ORIGINATION_COLUMNS:
            keep.append(c)
        elif c not in UNINFORMATIVE_COLUMNS:
            unknown.append(c)
    return keep, leak, unknown


def drop_leakage(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=find_leakage(df.columns))
