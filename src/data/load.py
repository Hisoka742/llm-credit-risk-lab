"""Locating and reading the raw Lending Club CSV."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from src.data.clean import parse_month

STRING_COLUMNS = frozenset(
    """
    id term grade sub_grade emp_title emp_length home_ownership verification_status desc
    purpose title zip_code addr_state initial_list_status application_type
    verification_status_joint disbursement_method
    """.split()
)
DATE_COLUMNS = frozenset({"issue_d", "earliest_cr_line", "sec_app_earliest_cr_line"})


def find_raw_file(raw_dir: str | Path, pattern: str, raw_file: str | None = None) -> Path:
    if raw_file:
        path = Path(raw_file)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    files = [p for p in Path(raw_dir).rglob(pattern) if p.is_file()]
    if not files:
        raise FileNotFoundError(
            f"No file matching {pattern!r} under {raw_dir}. Download with:\n"
            "  kaggle datasets download -d wordsforthewise/lending-club -p data/raw --unzip"
        )
    # Prefer the uncompressed CSV if both exist: parsing is much faster than gunzip + parse.
    return sorted(files, key=lambda p: (p.suffix == ".gz", str(p)))[0]


def read_header(path: Path) -> list[str]:
    return pd.read_csv(path, nrows=0).columns.tolist()


def iter_chunks(
    path: Path, usecols: list[str], chunksize: int, nrows: int | None = None
) -> Iterator[pd.DataFrame]:
    """Read as str so dtypes cannot differ between chunks. `coerce_types` runs after concat."""
    yield from pd.read_csv(
        path, usecols=usecols, dtype=str, chunksize=chunksize, nrows=nrows, low_memory=False
    )


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if col in DATE_COLUMNS:
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = parse_month(df[col])
        elif col in STRING_COLUMNS:
            df[col] = df[col].astype("string").str.strip()
        elif df[col].dtype == object:
            # Older releases format int_rate / revol_util as "13.56%".
            df[col] = pd.to_numeric(df[col].str.rstrip("%"), errors="coerce")
    return df
