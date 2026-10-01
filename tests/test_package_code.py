from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.package_code import package


def test_package_keeps_nested_data_package_and_drops_secrets(tmp_path) -> None:
    root = tmp_path / "repo"
    for rel in [
        "src/data/prepare.py", "src/features/x.py", "configs/base.yaml", ".env",
        "data/raw/big.csv", "data/processed/loans.parquet", "cache/llm/a.json",
        "src/__pycache__/m.pyc", "reports/runs/e0/predictions.parquet",
        "reports/runs/e0/metrics.json",
    ]:  # fmt: skip
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    names = package(root, tmp_path / "out.zip")
    assert "src/data/prepare.py" in names  # nested "data" package kept
    assert "reports/runs/e0/metrics.json" in names
    for gone in [".env", "data/raw/big.csv", "cache/llm/a.json", "src/__pycache__/m.pyc",
                 "reports/runs/e0/predictions.parquet"]:  # fmt: skip
        assert gone not in names
    assert zipfile.ZipFile(tmp_path / "out.zip").namelist() == names


def test_real_repo_package_is_importable_layout(tmp_path) -> None:
    names = package(Path(__file__).resolve().parents[1], tmp_path / "out.zip")
    assert {"src/data/__init__.py", "src/data/load.py", "scripts/llm_extract.py"} <= set(names)
    assert not any(n.endswith(".env") or n.startswith("data/") for n in names)
