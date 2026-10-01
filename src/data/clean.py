"""Cleaning of the borrower free-text `desc` and light type coercion of raw columns."""

from __future__ import annotations

import html
import re

import pandas as pd

# Listing edits are prefixed with "Borrower added on 08/18/12 >". Loans from 2007-2009 use the
# member id instead of "Borrower", e.g. "547198 added on 10/19/09 >". The date and the id carry
# no borrower signal (the id could even act as a join key), so both forms are stripped.
_ADDED_ON = re.compile(r"(?:Borrower|\d+)\s+added on \d{1,2}/\d{1,2}/\d{2,4}\s*>", re.IGNORECASE)
_BR = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
# Only real tags: "<" must be directly followed by a letter or "/". Borrowers write literal
# comparisons such as "< 40% of available credit, to > 80%", which a naive <[^>]+> would delete.
_TAG = re.compile(r"</?[a-zA-Z][^<>]*>")
_WS = re.compile(r"\s+")


def clean_desc(text: object) -> str:
    """Return cleaned description text, or "" for missing/empty input."""
    if not isinstance(text, str):
        return ""
    t = _BR.sub(" ", text)
    t = _TAG.sub(" ", t)
    t = html.unescape(t)  # after tag removal, so an escaped "&lt;b&gt;" stays as text
    t = _ADDED_ON.sub(" ", t)
    return _WS.sub(" ", t).strip()


def clean_desc_series(s: pd.Series) -> pd.Series:
    out = pd.Series("", index=s.index, dtype=object)
    mask = s.notna()
    out[mask] = s[mask].map(clean_desc)
    return out


def parse_month(s: pd.Series) -> pd.Series:
    """Parse Lending Club month strings like 'Dec-2015' (older releases use 'Dec-15')."""
    out = pd.to_datetime(s, format="%b-%Y", errors="coerce")
    retry = out.isna() & s.notna()
    if retry.any():
        out[retry] = pd.to_datetime(s[retry], format="%b-%y", errors="coerce")
    return out
