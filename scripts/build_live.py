"""Build the bundle the live demo serves: the trained E2 model and a few real borrower profiles.

    python -m scripts.run_experiment --config configs/e2.yaml   # writes reports/runs/e2/model.cbm
    python -m scripts.build_live                                # -> data/processed/live/

Profiles are real *test* loans (never seen in training), picked deterministically: a spread of
grades, both outcomes, and descriptions long enough to be worth rewriting. Each keeps its full
E2 feature row, so the service can change the text features and nothing else.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from src.config import load_config
from src.features.assemble import assemble_features, llm_features_path
from src.features.llm_extract import FIELDS

GRADES = ["A", "B", "C", "D", "E", "F"]


def pick_profiles(df: pd.DataFrame, seed: int, per_grade: int = 2) -> pd.DataFrame:
    """One repaid and one defaulted test loan per grade, with a 150 to 600 character text."""
    n = df["desc"].str.len()
    pool = df[(df["split"] == "test") & n.between(150, 600) & df["grade"].isin(GRADES)]
    picks = []
    for grade in GRADES:
        for target in (0, 1)[:per_grade]:
            g = pool[(pool["grade"] == grade) & (pool["target"] == target)]
            if len(g):
                picks.append(g.sample(1, random_state=seed))
    return pd.concat(picks)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/e2.yaml")
    ap.add_argument("--out", default=None, help="default: <processed dir>/live")
    args = ap.parse_args()

    cfg = load_config(args.config)
    name = cfg["experiment"]["name"]
    runs = Path(cfg["paths"]["reports_dir"]) / "runs"
    model_path = runs / name / "model.cbm"
    if not model_path.exists():
        raise SystemExit(f"{model_path} missing. Run: python -m scripts.run_experiment "
                         f"--config {args.config}")  # fmt: skip
    processed = Path(cfg["paths"]["processed"])
    out = Path(args.out) if args.out else processed.parent / "live"
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(processed)
    X, cat_cols, _ = assemble_features(cfg, df, (df["split"] == "train").to_numpy())
    metrics = json.loads((runs / name / "metrics.json").read_text())
    if list(X.columns) != metrics["features"]:
        raise SystemExit("Feature columns differ from the saved run. Rerun the experiment.")

    chosen = pick_profiles(df, cfg["seed"])
    e0 = pd.read_parquet(runs / "e0" / "predictions.parquet").set_index("id")["score"]
    e2 = pd.read_parquet(runs / name / "predictions.parquet").set_index("id")["score"]
    # Raw extraction values (not the model encoding), so the page shows what the LLM returned.
    llm = pd.read_parquet(llm_features_path(processed.parent, cfg["llm"]["model"]))
    llm = llm.drop_duplicates("id").set_index("id")[FIELDS]

    profiles = []
    for _, r in chosen.iterrows():
        profiles.append({
            "id": r["id"],
            "desc": r["desc"],
            "issued": r["issue_d"].strftime("%Y-%m"),
            "grade": r["grade"],
            "int_rate": float(r["int_rate"]),
            "loan_amnt": float(r["loan_amnt"]),
            "annual_inc": float(r["annual_inc"]),
            "purpose": r["purpose"],
            "defaulted": bool(r["target"] == 1),
            "pd_no_text": float(e0[r["id"]]),
            "pd_original_text": float(e2[r["id"]]),
            "original_reading": json.loads(llm.loc[[r["id"]]].to_json(orient="records"))[0],
        })  # fmt: skip

    Xp = X.loc[chosen.index].copy()
    Xp.insert(0, "id", chosen["id"].to_numpy())
    Xp.to_parquet(out / "profiles_X.parquet", index=False)
    shutil.copyfile(model_path, out / "model.cbm")
    (out / "bundle.json").write_text(
        json.dumps(
            {"experiment": name, "trained_on": cfg["llm"]["model"], "features": list(X.columns),
             "categorical": cat_cols, "profiles": profiles},
            indent=1, default=str,
        ),
        encoding="utf-8",
    )  # fmt: skip
    print(f"wrote {out}: {len(profiles)} profiles, {X.shape[1]} features, "
          f"model {model_path.stat().st_size / 1e6:.1f} MB")  # fmt: skip


if __name__ == "__main__":
    main()
