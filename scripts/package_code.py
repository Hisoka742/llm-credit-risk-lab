"""Zip the repo's code for upload as a Kaggle Dataset (no data, caches or secrets).

    python -m scripts.package_code            # -> dist/llm-credit-risk-lab-code.zip

Exclusions apply to *top-level* folders only (data/, cache/, ...). A nested package such as
src/data/ must be kept: an earlier version dropped every folder named "data", which broke
`import src.data` on Kaggle. Tests cover this.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

TOP_LEVEL_EXCLUDE = frozenset(
    # site/ (the showcase website and its node_modules) and .impeccable/ (design review
    # files) are not needed to run the Python pipeline on Kaggle.
    {
        "data",
        "cache",
        "dist",
        "catboost_info",
        ".git",
        ".claude",
        ".venv",
        "venv",
        "site",
        ".impeccable",
    }
)
ANYWHERE_EXCLUDE = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints"})
SECRET_NAMES = frozenset({".env", "kaggle.json"})
EXCLUDE_SUFFIXES = frozenset({".parquet", ".cbm", ".pkl"})  # large run artifacts


def include(rel: Path) -> bool:
    parts = rel.parts
    if parts[0] in TOP_LEVEL_EXCLUDE or ANYWHERE_EXCLUDE & set(parts):
        return False
    return rel.name not in SECRET_NAMES and rel.suffix not in EXCLUDE_SUFFIXES


def package(root: Path, out: Path) -> list[str]:
    files = sorted(
        p.relative_to(root) for p in root.rglob("*") if p.is_file() and include(p.relative_to(root))
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(root / rel, rel.as_posix())
    return [f.as_posix() for f in files]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", default="dist/llm-credit-risk-lab-code.zip")
    args = ap.parse_args()
    names = package(Path("."), Path(args.out))
    for required in ("src/data/prepare.py", "src/features/llm_extract.py", "configs/base.yaml"):
        if required not in names:
            raise SystemExit(f"package is missing {required}")
    print(f"wrote {args.out}: {len(names)} files")


if __name__ == "__main__":
    main()
