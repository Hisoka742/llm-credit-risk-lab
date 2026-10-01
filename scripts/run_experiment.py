"""Train one experiment and evaluate it on the out-of-time test set.

    python -m scripts.run_experiment --config configs/e0.yaml
    python -m scripts.run_experiment --config configs/e1.yaml     # needs scripts.embed first
    python -m scripts.run_experiment --config configs/e2.yaml     # needs scripts.llm_extract
    python -m scripts.run_experiment --config configs/e4.yaml     # TF-IDF + LR, text only
    python -m scripts.run_experiment --config configs/e0.yaml --llm-sample

--llm-sample restricts train/val/test to the fixed LLM sample (llm_sample_ids.parquet) and
suffixes the run name with `_s`, so E0-E4 can be compared on identical loans when
`llm.sample_size` is smaller than the full data.

Writes reports/runs/<exp>/{metrics.json, predictions.parquet, feature_importance.csv}
and reports/figures/<exp>_{calibration,gini_by_quarter}.png. If the config names a
`baseline`, it also runs a paired bootstrap against that run's saved test predictions.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import load_config
from src.eval import metrics as M
from src.eval.compare import compare_to_baseline, load_predictions
from src.eval.plots import plot_calibration, plot_gini_by_period, plot_shap_by_value
from src.eval.shap_analysis import by_value_table, importance_table, shap_values
from src.features.assemble import assemble_features
from src.models.catboost_model import fit_catboost, predict_pd
from src.models.text_baseline import fit_tfidf_logreg, predict_text, top_terms


def _fmt_ci(r: dict[str, float]) -> str:
    return f"{r['value']:.4f}  [{r['ci_low']:.4f}, {r['ci_high']:.4f}]"


def _fmt_diff(r: dict[str, float]) -> str:
    return f"{r['diff']:+.4f}  [{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]"


def _train_catboost(
    cfg: dict, df: pd.DataFrame, y: pd.Series, is_: dict, out_dir: Path
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    X, cat_cols, info = assemble_features(cfg, df, is_["train"])
    n_const = len(info["dropped_constant_in_train"])
    print(f"[{cfg['experiment']['name']}] {X.shape[1]} features ({len(cat_cols)} categorical); "
          f"dropped {n_const} constant/all-missing in train")  # fmt: skip
    model = fit_catboost(
        X[is_["train"]], y[is_["train"]], X[is_["val"]], y[is_["val"]],
        cat_cols, cfg["catboost"], cfg["seed"],
    )  # fmt: skip
    score = predict_pd(model, X, cat_cols)
    imp = pd.Series(model.get_feature_importance(), index=X.columns)
    info.update(
        n_features=X.shape[1], features=list(X.columns), categorical=cat_cols,
        best_iteration=int(model.get_best_iteration()),
    )  # fmt: skip

    llm_cols = [c for c in X.columns if c.startswith("llm_")]
    if llm_cols:
        sv, Xs = shap_values(model, X[is_["test"]], cat_cols, cfg["shap"]["max_rows"], cfg["seed"])
        tab = importance_table(sv)
        tab.to_csv(out_dir / "shap_importance.csv", index_label="feature")
        by_val = by_value_table(sv, Xs, llm_cols)
        by_val.to_csv(out_dir / "shap_llm_by_value.csv", index=False)
        info["shap_llm"] = {
            "n_rows": len(sv),
            "llm_share_of_total_abs_shap": float(tab.loc[llm_cols, "share"].sum()),
            "ranks": {c: int(tab.loc[c, "rank"]) for c in llm_cols},
            "mean_abs_shap": {c: float(tab.loc[c, "mean_abs_shap"]) for c in llm_cols},
        }
        fig = Path(cfg["paths"]["reports_dir"]) / "figures" / f"{out_dir.name}_shap_llm.png"
        plot_shap_by_value(by_val, f"{out_dir.name.upper()} mean SHAP by LLM feature value", fig)
    return score, imp, info


def _train_tfidf(
    cfg: dict, df: pd.DataFrame, y: pd.Series, is_: dict, out_dir: Path
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    text = df["desc"].astype(str)
    vec, lr, info = fit_tfidf_logreg(
        text[is_["train"]], y[is_["train"]], text[is_["val"]], y[is_["val"]],
        cfg["tfidf"], cfg["seed"],
    )  # fmt: skip
    print(f"[{cfg['experiment']['name']}] TF-IDF vocab {info['vocab_size']:,}, C={info['C']} "
          f"(val AUC by C: {info['val_auc_by_C']})")  # fmt: skip
    score = pd.Series(predict_text(vec, lr, text), index=df.index, name="score")
    terms = top_terms(vec, lr)
    terms.to_csv(out_dir / "top_terms.csv", index=False)
    imp = terms.set_index("term")["coef"]
    info["top_default_terms"] = terms.head(15)["term"].tolist()
    info["top_repay_terms"] = terms.tail(15)["term"].tolist()[::-1]
    return score, imp, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--llm-sample", action="store_true", help="restrict to the fixed LLM sample")
    args = ap.parse_args()

    cfg = load_config(args.config)
    exp = cfg["experiment"]
    suffix = "_s" if args.llm_sample else ""
    name, seed, ecfg = exp["name"] + suffix, cfg["seed"], cfg["eval"]
    runs_dir = Path(cfg["paths"]["reports_dir"]) / "runs"
    out_dir = runs_dir / name
    fig_dir = Path(cfg["paths"]["reports_dir"]) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(cfg["paths"]["processed"])
    if args.llm_sample:
        ids = pd.read_parquet(Path(cfg["paths"]["processed"]).parent / "llm_sample_ids.parquet")
        df = df[df["id"].isin(ids["id"])].reset_index(drop=True)
        print(f"[{name}] restricted to LLM sample: {len(df):,} loans")
    is_ = {s: (df["split"] == s).to_numpy() for s in ("train", "val", "test")}
    y_all = df["target"].astype(int)

    t0 = time.perf_counter()
    trainer = _train_tfidf if exp.get("model", "catboost") == "tfidf_logreg" else _train_catboost
    score, imp, train_info = trainer(cfg, df, y_all, is_, out_dir)
    fit_s = time.perf_counter() - t0

    y = {s: y_all[m].to_numpy() for s, m in is_.items()}
    p = {s: score[m].to_numpy() for s, m in is_.items()}
    nb, ci = ecfg["n_bootstrap"], ecfg["ci"]

    test_gini = M.bootstrap_ci(y["test"], p["test"], M.gini, nb, seed, ci)
    test_auc = M.bootstrap_ci(y["test"], p["test"], M.auc, nb, seed, ci)
    test_brier = M.bootstrap_ci(y["test"], p["test"], M.brier, nb, seed, ci)
    quarter = df.loc[is_["test"], "issue_d"].dt.to_period("Q").astype(str)
    by_q = M.gini_by_period(y["test"], p["test"], quarter, nb, seed, ci, min_n=ecfg["min_period_n"])
    calib = {s: M.calibration_table(y[s], p[s], ecfg["calibration_bins"]) for s in ("val", "test")}

    preds = pd.DataFrame(
        {"id": df["id"], "issue_d": df["issue_d"], "split": df["split"], "target": y_all,
         "score": score.to_numpy()}
    )  # fmt: skip
    metrics: dict[str, Any] = {
        "experiment": name,
        "description": exp["description"],
        "config": args.config,
        "llm_sample": args.llm_sample,
        "model": exp.get("model", "catboost"),
        "seed": seed,
        **train_info,
        "fit_seconds": round(fit_s, 1),
        "n": {s: int(m.sum()) for s, m in is_.items()},
        "default_rate": {s: float(y[s].mean()) for s in y},
        "gini": {
            "train_in_sample": M.gini(y["train"], p["train"]),
            "val_used_for_model_selection": M.gini(y["val"], p["val"]),
            "test": test_gini,
        },
        "auc_test": test_auc,
        "brier_test": test_brier,
        "brier_skill_test": M.brier_skill(y["test"], p["test"]),
        "mean_pd_test": float(p["test"].mean()),
        "psi_score": {
            "train_vs_val": M.psi(p["train"], p["val"]),
            "train_vs_test": M.psi(p["train"], p["test"]),
            "val_vs_test": M.psi(p["val"], p["test"]),
        },
        "gini_by_quarter_test": by_q.to_dict(orient="records"),
        "calibration_test": calib["test"].to_dict(orient="records"),
    }
    base_name = exp.get("baseline") and exp["baseline"] + suffix
    if base_name:
        base = load_predictions(runs_dir, base_name)
        metrics[f"vs_{base_name}"] = compare_to_baseline(
            preds, base, nb, seed, ci, min_period_n=ecfg["min_period_n"]
        )

    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    preds.to_parquet(out_dir / "predictions.parquet", index=False)
    imp.sort_values(ascending=False).rename("importance").to_csv(out_dir / "feature_importance.csv")

    plot_calibration({"validation": calib["val"], "test": calib["test"]},
                     f"{name.upper()} calibration by score decile",
                     fig_dir / f"{name}_calibration.png")  # fmt: skip
    plot_gini_by_period(by_q, f"{name.upper()} test Gini by issue quarter",
                        fig_dir / f"{name}_gini_by_quarter.png")  # fmt: skip

    # ---- console summary ----
    pd.set_option("display.width", 160)
    print(f"\n==== {name.upper()} ({exp['description']}) ====")
    if "embeddings" in train_info:
        e = train_info["embeddings"]
        print(f"embeddings: {e['model']} {e['dim']}d -> {e['n_components']} PCs "
              f"({e['explained_variance_ratio_total']:.1%} of train variance)")  # fmt: skip
    if "llm" in train_info:
        print(f"llm: {train_info['llm']['model']}, null rate {train_info['llm']['null_rate']:.2%}")
    if "best_iteration" in train_info:
        print(f"best iteration {train_info['best_iteration']}, fit {fit_s:.0f}s")
    print(f"Gini train (in-sample)  {metrics['gini']['train_in_sample']:.4f}")
    print(f"Gini val (model select) {metrics['gini']['val_used_for_model_selection']:.4f}")
    print(f"Gini test               {_fmt_ci(test_gini)}")
    print(f"AUC  test               {_fmt_ci(test_auc)}")
    print(
        f"Brier test              {_fmt_ci(test_brier)}   skill {metrics['brier_skill_test']:.4f}"
    )
    print(f"Mean PD test {metrics['mean_pd_test']:.4f} vs observed {y['test'].mean():.4f}")
    ps = metrics["psi_score"]
    print("PSI score  " + "  ".join(f"{k} {v:.4f}" for k, v in ps.items()))
    print("\nGini by issue quarter (test, periods with n >= min_period_n):")
    print(by_q.dropna(subset=["gini"]).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\nTop 15 by importance:")
    print(imp.sort_values(ascending=False).head(15).round(3).to_string())
    if "shap_llm" in train_info:
        s = train_info["shap_llm"]
        ranks = sorted(s["ranks"].items(), key=lambda kv: kv[1])
        print(f"\nLLM features: {s['llm_share_of_total_abs_shap']:.1%} of total |SHAP|; ranks "
              + ", ".join(f"{k}={v}" for k, v in ranks))  # fmt: skip
    if base_name:
        c = metrics[f"vs_{base_name}"]
        gd = c["gini_diff"]
        print(f"\n== {name.upper()} vs {base_name.upper()} (paired bootstrap, {nb} resamples, "
              f"same {c['n']:,} test loans) ==")  # fmt: skip
        print(f"Gini  {c['gini_new']:.4f} vs {c['gini_base']:.4f}   diff {_fmt_diff(gd)}"
              f"   P(diff <= 0) = {gd['p_value_one_sided']:.3f}")  # fmt: skip
        print(f"Brier diff {_fmt_diff(c['brier_diff'])}   (negative = {name} better)")
        for r in c["gini_diff_by_quarter"]:
            print(f"  {r['period']}  n={r['n']:,}  Gini diff {_fmt_diff(r)}")
    print(f"\nWrote {out_dir}/ and {fig_dir}/{name}_*.png")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
