"""Export everything the showcase site displays to site/src/data/study.json.

    python -m scripts.export_site_data

The site never hard-codes a number: each value here is read from the repo's own outputs
(reports/runs/*/metrics.json, reports/data/prepare_data.json, the leakage lists, the E4 text
model) so the page and results.md cannot disagree. Experiments without a metrics.json are
exported as pending, never estimated.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from src.config import load_config
from src.features.assemble import llm_features_path
from src.features.leakage import LEAKAGE_COLUMNS, PRE_ORIGINATION_COLUMNS

EXPERIMENTS = {
    "e0": "Tabular baseline",
    "e1": "Tabular + embeddings",
    "e2": "Tabular + LLM features",
    "e3": "Tabular + embeddings + LLM",
    "e4": "Text only (TF-IDF)",
}


def _count_tests() -> int | None:
    """Number of collected pytest tests, so the site's figure tracks the suite."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, timeout=300, check=False,
        ).stdout  # fmt: skip
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+) tests? collected", out)
    return int(m.group(1)) if m else None


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _experiment(runs: Path, key: str) -> dict[str, Any]:
    m = _load(runs / key / "metrics.json")
    if not m:
        return {"id": key, "label": EXPERIMENTS[key], "status": "pending"}
    out: dict[str, Any] = {
        "id": key,
        "label": EXPERIMENTS[key],
        "status": "done",
        "source": f"reports/runs/{key}/metrics.json",
        "n_features": m.get("n_features"),
        "gini": m["gini"]["test"],
        "auc": m["auc_test"],
        "brier": m["brier_test"],
        "brier_skill": m["brier_skill_test"],
        "mean_pd": m["mean_pd_test"],
        "observed": m["default_rate"]["test"],
        "psi_train_test": m["psi_score"]["train_vs_test"],
        "calibration": m["calibration_test"],
        "by_quarter": [q for q in m["gini_by_quarter_test"] if q.get("gini") == q.get("gini")],
    }
    out["by_quarter"] = [q for q in out["by_quarter"] if q.get("gini") is not None]
    if "shap_llm" in m:
        out["llm_shap_share"] = m["shap_llm"]["llm_share_of_total_abs_shap"]
    vs = m.get("vs_e0")
    if vs:
        out["vs_e0"] = {"gini": vs["gini_diff"], "brier": vs["brier_diff"], "n": vs["n"]}
    return out


def _word_weights(df: pd.DataFrame, cfg: dict, C: float, texts: list[str]) -> dict[str, float]:
    """Unigram coefficients of a TF-IDF + logistic model, for the words in `texts` only.

    Same recipe as E4 but unigrams, so each displayed word has one weight. Fit on train rows.
    Positive = associated with default. The model itself keeps every word; only the export
    leaves out common filler words (the, my, would), whose large weights reflect frequency
    rather than meaning, so the page colours content words. The site says so in its caption.
    """
    train = df[df["split"] == "train"]
    vec = TfidfVectorizer(ngram_range=(1, 1), min_df=cfg["tfidf"]["min_df"], sublinear_tf=True,
                          strip_accents="unicode", lowercase=True)  # fmt: skip
    X = vec.fit_transform(train["desc"].astype(str))
    lr = LogisticRegression(C=C, max_iter=2000, solver="liblinear", random_state=cfg["seed"])
    lr.fit(X, train["target"])
    coef = dict(zip(vec.get_feature_names_out(), lr.coef_[0], strict=True))
    analyzer = vec.build_analyzer()
    wanted = {w for t in texts for w in analyzer(t)}
    return {
        w: round(float(coef[w]), 4)
        for w in sorted(wanted)
        if w in coef and w not in ENGLISH_STOP_WORDS
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/e4.yaml")
    ap.add_argument("--out", default="site/src/data/study.json")
    args = ap.parse_args()

    cfg = load_config(args.config)
    reports = Path(cfg["paths"]["reports_dir"])
    runs = reports / "runs"
    df = pd.read_parquet(cfg["paths"]["processed"])
    prep = _load(reports / "data" / "prepare_data.json") or {}

    experiments = [_experiment(runs, k) for k in EXPERIMENTS]
    e4 = _load(runs / "e4" / "metrics.json") or {}

    pilot = _load(reports / "pilot" / "qwen2.5-7b_pilot20.json") or {}
    listings = []
    by_id = df.set_index("id")
    for loan_id, values in pilot.get("outputs", {}).items():
        if loan_id not in by_id.index:
            continue
        row = by_id.loc[loan_id]
        review = pilot.get("review", {}).get(loan_id)
        listings.append({
            "id": loan_id,
            "desc": row["desc"],
            "year": int(row["issue_d"].year),
            "grade": row["grade"],
            "purpose": row["purpose"],
            "defaulted": bool(row["target"] == 1),
            "split": str(row["split"]),
            "llm": dict(zip(pilot["fields"], values, strict=True)),
            "review": review,
        })  # fmt: skip

    weights = _word_weights(df, cfg, float(e4.get("C", 0.1)), [x["desc"] for x in listings])

    short = df["desc"].str.strip()
    phrases = short[short.str.split().str.len() <= 4].str.lower().str.rstrip(".").value_counts()

    terms = pd.read_csv(runs / "e4" / "top_terms.csv") if (runs / "e4" / "top_terms.csv").exists() \
        else pd.DataFrame(columns=["term", "coef"])  # fmt: skip
    emb_cost = _load(runs / f"embed_{cfg['embeddings']['model_name'].split('/')[-1]}" / "cost.json")

    lowering = terms[terms["coef"] < 0].sort_values("coef")

    # Full-run extraction record: cost from the run's own cost.json, null count from the
    # feature file. Absent until the extraction has finished.
    llm_model = cfg["llm"]["model"]
    llm_cost = _load(runs / f"llm_{llm_model.split('/')[-1]}" / "cost.json")
    llm_path = llm_features_path(Path(cfg["paths"]["processed"]).parent, llm_model)
    llm_run = None
    if llm_cost and llm_path.exists():
        ok = pd.read_parquet(llm_path, columns=["llm_ok"])["llm_ok"]
        llm_run = {
            "model": llm_model, "n": int(len(ok)), "n_null": int((~ok).sum()),
            "n_timed_calls": llm_cost["n_fresh_calls"],
            "mean_prompt_tokens": llm_cost["mean_prompt_tokens"],
            "mean_completion_tokens": llm_cost["mean_completion_tokens"],
            "gpu_seconds_per_application": llm_cost["accelerator_seconds_per_application"],
        }  # fmt: skip

    study = {
        "funnel": prep.get("funnel", []),
        "coverage_by_year": [
            {"year": r["year"], "loans": r["n_loans"], "with_desc": r["n_with_desc"],
             "coverage": r["coverage_all"]}
            for r in prep.get("desc_coverage_by_year", [])
        ],
        "splits": prep.get("splits", []),
        "leakage": {
            # loan_status is on the denylist as the label itself; the site lists the
            # post-origination columns, matching the count prepare_data reports.
            "denied": [
                {"column": c, "reason": r} for c, r in LEAKAGE_COLUMNS.items() if c != "loan_status"
            ],
            "n_denied": len(LEAKAGE_COLUMNS) - 1,
            "n_allowed": len(PRE_ORIGINATION_COLUMNS),
        },
        "experiments": experiments,
        "terms": {
            "raise": terms[terms["coef"] > 0].head(14).to_dict(orient="records"),
            "lower": lowering.head(14).to_dict(orient="records"),
        },
        "word_weights": weights,
        "phrases": [{"text": t, "n": int(n)} for t, n in phrases.head(24).items()],
        "listings": listings,
        "pilot": {"model": pilot.get("model"), "source": pilot.get("source"),
                  "cost": pilot.get("cost")},
        "llm_run": llm_run,
        "embedding_cost": emb_cost and {
            "model": emb_cost["model_name"], "device": emb_cost["device"],
            "mean_tokens": emb_cost["mean_tokens"],
            "ms_per_application": 1000 / emb_cost["texts_per_second"],
            "n_texts": emb_cost["n_computed"], "minutes": emb_cost["seconds"] / 60,
        },
        "totals": {
            "loans": int(len(df)),
            "defaults": int(df["target"].sum()),
            "default_rate": float(df["target"].mean()),
            "test_loans": int((df["split"] == "test").sum()),
            "unique_texts": int(df["desc"].nunique()),
            "n_bootstrap": cfg["eval"]["n_bootstrap"],
            "tests": _count_tests(),
        },
    }  # fmt: skip

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(study, indent=1, default=float), encoding="utf-8")
    done = [e["id"] for e in experiments if e["status"] == "done"]
    print(f"wrote {out}: experiments done {done}, {len(listings)} listings, "
          f"{len(weights)} word weights")  # fmt: skip


if __name__ == "__main__":
    main()
