# LLM Credit Risk Lab

## Goal
Research project: do LLM-derived features from borrower free text improve a classical credit-risk (PD) model?
Output is a reproducible study with honest results — a positive, negative or mixed finding is all fine,
as long as it is measured correctly. Target audience: a bank risk-modeling / LLM-research team.

## Research questions
1. Does adding text embeddings of borrower descriptions to a GBDT baseline improve Gini on an out-of-time test set?
2. Do structured features extracted by an LLM (JSON) help more than raw embeddings, and are they more interpretable?
3. Are improvements stable over time (PSI, Gini per quarter) and statistically significant (bootstrap CI)?
4. What does it cost (latency, tokens) per application?

## Data
- Kaggle: `wordsforthewise/lending-club`, file `accepted_2007_to_2018Q4.csv(.gz)`.
- Text fields: `desc` (borrower description — mostly filled only for loans issued before ~2014; verify coverage), `title`, `emp_title`.
- Target: `loan_status` in {Fully Paid} -> 0, {Charged Off, Default, "Does not meet the credit policy. Status:Charged Off"} -> 1. Drop Current / Late / In Grace Period (unfinished outcomes).
- Keep only rows where `desc` is non-empty after cleaning (strip "Borrower added on MM/DD/YY >" prefixes and HTML like `<br>`). Report how many rows remain.
- LEAKAGE — must drop all post-origination columns: total_pymnt*, total_rec_*, recoveries, collection_recovery_fee, last_pymnt_*, next_pymnt_d, out_prncp*, last_credit_pull_d, last_fico_*, hardship_*, settlement_*, debt_settlement_flag, funded_amnt_inv, pymnt_plan, and anything else only known after the loan was issued. Keep a documented list in `src/features/leakage.py`.
- Split by `issue_d` (out-of-time): train on earliest ~70%, validation next ~15%, test latest ~15%. Never random split.

## Experiments (same split, same CatBoost settings, same seeds)
- E0: CatBoost on tabular features only (baseline).
- E1: E0 + sentence embeddings of `desc` (e.g. `BAAI/bge-small-en-v1.5` or `intfloat/e5-base-v2`; text is English), reduced with PCA/SVD fit on train only.
- E2: E0 + LLM-extracted structured features from `desc` (JSON schema below).
- E3: E0 + E1 + E2.
- E4 (optional): TF-IDF + logistic regression on text alone, as a cheap text baseline.

LLM JSON schema (validate with pydantic; invalid -> retry once, then null):
```
loan_purpose_category: enum[debt_consolidation, credit_card, home, business, medical, education, car, other]
financial_stress: int 0-3
employment_stability: int 0-3
mentions_other_debts: bool
mentions_job_loss_or_income_drop: bool
mentions_medical_or_family_emergency: bool
has_repayment_plan: bool
text_quality: int 0-3   # clarity/coherence of the description
```
LLM backend must be pluggable (OpenAI-compatible client: GigaChat, vLLM on Kaggle with Qwen2.5-7B-Instruct, or any API).
Cache every LLM response on disk keyed by hash(model + prompt + text) so reruns cost nothing.
Allow running LLM extraction on a sample (config `llm.sample_size`) — all experiments comparing E2/E3 must use the same sample.

## Metrics & analysis
- ROC-AUC and Gini = 2*AUC - 1 on test; bootstrap 95% CI (1000 resamples); paired bootstrap for the difference vs E0.
- Brier score, calibration curve (reliability plot).
- Gini by issue quarter on test; PSI of model score between train and test.
- SHAP summary for E2/E3 — which LLM features matter.
- Cost table: avg tokens, latency and $ (or GPU-seconds) per application for E1/E2.
- Error analysis: 20 examples where E2 disagrees most with E0, with the LLM JSON shown.

## Repo layout
```
configs/            # yaml configs, one per experiment
data/raw/           # gitignored
data/processed/     # gitignored, parquet
src/data/           # load, clean, target, split
src/features/       # tabular, leakage list, embeddings, llm_extract
src/models/         # train/eval catboost
src/eval/           # metrics, bootstrap, psi, calibration, shap
scripts/            # CLI entry points: prepare_data, embed, llm_extract, run_experiment, make_report
notebooks/          # only for exploration + final figures
reports/            # results.md, figures/
tests/              # pytest: leakage check, split is time-ordered, schema validation, metric functions
```

## Engineering rules
- Python 3.10+, type hints, `pyproject.toml`, `ruff`.
- All randomness seeded from config. Every run writes metrics to `reports/runs/<exp>/metrics.json`.
- One command per step, e.g. `python -m scripts.run_experiment --config configs/e0.yaml`.
- Must run on CPU for E0 and on a free Kaggle/Colab T4 for embeddings and LLM extraction.
- Write a test that fails if any leakage column survives into the feature matrix.
- README: problem, data, method, results table (with CIs), plots, limitations, how to reproduce.
- Explain non-obvious choices in comments or in README — the author must be able to defend every decision in an interview.
