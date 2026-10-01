"""Raw CSV -> one processed parquet with `target` and `split`, plus audit statistics.

Filter order (each step is counted):
  1. raw rows
  2. parsable issue_d (drops the footer rows "Total amount funded in policy code ...")
  3. finished outcome (target is 0/1)
  4. non-empty cleaned desc
  5. unique id
Description coverage is measured *before* step 4, on all dated rows and on finished rows,
so it shows how much the text filter shrinks each vintage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.clean import clean_desc_series, parse_month
from src.data.load import coerce_types, iter_chunks, read_header
from src.data.split import SPLITS, SplitBoundaries, assign_split, compute_boundaries
from src.data.target import make_target
from src.features.leakage import assert_no_leakage, partition_columns


@dataclass
class PrepareResult:
    df: pd.DataFrame
    funnel: list[tuple[str, int]]
    coverage: pd.DataFrame
    splits: pd.DataFrame
    boundaries: SplitBoundaries
    dropped_leakage: list[str] = field(default_factory=list)
    dropped_unreviewed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "funnel": [{"step": s, "rows": n} for s, n in self.funnel],
            "desc_coverage_by_year": self.coverage.reset_index().to_dict(orient="records"),
            "splits": self.splits.reset_index()
            .astype({"first_month": str, "last_month": str})
            .to_dict(orient="records"),
            "boundaries": {
                "train_end": str(self.boundaries.train_end.date()),
                "val_end": str(self.boundaries.val_end.date()),
            },
            "dropped_leakage_columns": self.dropped_leakage,
            "dropped_unreviewed_columns": self.dropped_unreviewed,
            "n_columns_out": int(self.df.shape[1]),
        }


def _coverage_counts(chunk: pd.DataFrame, has_desc: pd.Series, finished: pd.Series) -> pd.DataFrame:
    g = pd.DataFrame(
        {
            "year": chunk["issue_d"].dt.year,
            "n_loans": 1,
            "n_with_desc": has_desc.astype(int),
            "n_finished": finished.astype(int),
            "n_finished_with_desc": (finished & has_desc).astype(int),
            "n_bad_with_desc": (finished & has_desc & chunk["target"].eq(1).fillna(False)).astype(
                int
            ),
        }
    )
    return g.groupby("year").sum()


def split_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("split", observed=False)
    out = pd.DataFrame(
        {
            "rows": g.size(),
            "defaults": g["target"].sum().astype(int),
            "first_month": g["issue_d"].min().dt.strftime("%Y-%m"),
            "last_month": g["issue_d"].max().dt.strftime("%Y-%m"),
        }
    ).reindex(list(SPLITS))
    out["share"] = out["rows"] / out["rows"].sum()
    out["default_rate"] = out["defaults"] / out["rows"]
    return out


def prepare(
    raw_path: Path,
    *,
    chunksize: int,
    min_desc_chars: int,
    train_frac: float,
    val_frac: float,
    nrows: int | None = None,
) -> PrepareResult:
    header = read_header(raw_path)
    keep, leak, unreviewed = partition_columns(header)
    if "desc" not in keep or "issue_d" not in keep or "id" not in keep:
        raise ValueError("raw file lacks id/issue_d/desc")
    # loan_status is on the leakage list (it is the label) but is needed to build the target.
    usecols = keep + ["loan_status"]

    n_raw = n_dated = n_finished = n_desc = 0
    parts: list[pd.DataFrame] = []
    cov_parts: list[pd.DataFrame] = []
    for chunk in iter_chunks(raw_path, usecols, chunksize, nrows):
        n_raw += len(chunk)
        chunk["issue_d"] = parse_month(chunk["issue_d"])
        chunk = chunk[chunk["issue_d"].notna()].copy()
        n_dated += len(chunk)

        chunk["target"] = make_target(chunk["loan_status"])
        chunk["desc"] = clean_desc_series(chunk["desc"])
        finished = chunk["target"].notna()
        has_desc = chunk["desc"].str.len() >= min_desc_chars
        cov_parts.append(_coverage_counts(chunk, has_desc, finished))

        n_finished += int(finished.sum())
        chunk = chunk[finished & has_desc].drop(columns=["loan_status"])
        n_desc += len(chunk)
        parts.append(chunk)

    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates(subset="id", keep="first")
    funnel = [
        ("raw rows", n_raw),
        ("valid issue_d", n_dated),
        ("finished outcome (target 0/1)", n_finished),
        (f"non-empty desc (>= {min_desc_chars} chars after cleaning)", n_desc),
        ("unique id", len(df)),
    ]

    df = coerce_types(df)
    df["target"] = df["target"].astype("int8")
    df = df.sort_values(["issue_d", "id"], kind="stable").reset_index(drop=True)
    boundaries = compute_boundaries(df["issue_d"], train_frac, val_frac)
    df["split"] = assign_split(df["issue_d"], boundaries)
    assert_no_leakage(df.columns)

    cov = pd.concat(cov_parts).groupby(level=0).sum()
    cov.index = cov.index.astype(int)
    cov["coverage_all"] = cov["n_with_desc"] / cov["n_loans"]
    cov["coverage_finished"] = cov["n_finished_with_desc"] / cov["n_finished"].where(
        cov["n_finished"] > 0
    )
    cov["default_rate_with_desc"] = cov["n_bad_with_desc"] / cov["n_finished_with_desc"].where(
        cov["n_finished_with_desc"] > 0
    )
    cov = cov.drop(columns="n_bad_with_desc")

    return PrepareResult(
        df=df,
        funnel=funnel,
        coverage=cov,
        splits=split_summary(df),
        boundaries=boundaries,
        dropped_leakage=[c for c in leak if c != "loan_status"],
        dropped_unreviewed=unreviewed,
    )
