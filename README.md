# LLM Credit Risk Lab

**Question.** Do features derived from borrowers' free-text loan descriptions improve a
classical probability-of-default (PD) model? If so, do structured LLM-extracted features
help more, and are they more interpretable, than raw text embeddings? What do they cost per
application?

**Status.** All five experiments are done: tabular baseline (E0), embeddings (E1), LLM
features (E2), both (E3) and a text-only baseline (E4). The LLM features come from
Qwen2.5-7B-Instruct (4-bit AWQ) served by vLLM on free Kaggle T4 GPUs
([kaggle_e2_llm_extract.ipynb](notebooks/kaggle_e2_llm_extract.ipynb)), run over all 125,700
descriptions. Full write-up: **[reports/results.md](reports/results.md)**.

**Answer.** On this data, no. Neither embeddings nor LLM-extracted features improve the
out-of-time Gini of a strong tabular model by an amount that can be told apart from zero.

## Results (out-of-time test set: loans issued Dec 2013 – Mar 2014, n = 19,858)

95% percentile-bootstrap CIs over test loans (1000 resamples). ΔGini uses a **paired**
bootstrap against E0 on the same loans.

| exp | features | Gini [95% CI] | AUC | Brier | ΔGini vs E0 [95% CI] | p (Δ≤0) |
|---|---|---|---|---|---|---|
| E0 | 72 tabular, CatBoost | 0.417 [0.398, 0.435] | 0.708 | 0.1228 | – | – |
| E1 | E0 + 32 PCA comps of bge-small `desc` embeddings | 0.421 [0.403, 0.440] | 0.710 | 0.1224 | +0.004 [−0.002, +0.010] | 0.079 |
| E2 | E0 + 8 LLM-extracted JSON features | 0.418 [0.399, 0.437] | 0.709 | 0.1225 | +0.001 [−0.003, +0.006] | 0.254 |
| E3 | E0 + E1 + E2 | 0.420 [0.402, 0.440] | 0.710 | 0.1223 | +0.004 [−0.003, +0.010] | 0.131 |
| E4 | TF-IDF + logistic regression, `desc` only | 0.189 [0.167, 0.210] | 0.595 | 0.1307 | −0.227 [−0.253, −0.202] | 1.000 |

**Reading.**
- **RQ1 (embeddings).** +0.004 Gini, **not significant** at 95% (p = 0.079).
- **RQ2 (LLM features).** +0.001 Gini, not significant (p = 0.254), so they help less than
  embeddings, not more. Adding them to embeddings (E3) gives no more than embeddings alone.
  They are more interpretable: each is a named field with a SHAP value, and together they
  carry 8.8% of total |SHAP| in E2. The model uses them, but that does not turn into better
  ranking on the test set.
- **Why so little.** The descriptions do carry signal on their own (E4 reaches Gini 0.19),
  but it overlaps with what the tabular model already knows: `purpose`, and Lending Club's
  own `grade` and `int_rate`, set by people who saw the same text.
- **RQ3 (stability).** All CatBoost models are well calibrated with score PSI < 0.01. The
  per-quarter differences vs E0 change sign between the two usable test quarters, which is
  what noise looks like.
- **RQ4 (cost).** Embeddings: about 20 ms per application on a laptop CPU. LLM extraction:
  453 prompt + 83 completion tokens and 0.46 GPU-seconds per application on a T4.
- Every experiment is a single seed. Differences of a few thousandths of Gini are comparable
  to training noise, so the ordering E1 > E3 > E2 > E0 should not be read as a ranking.
- `text_quality`, the most-used LLM feature, rises with description length, so it may partly
  measure how much the borrower wrote.

Figures: [calibration](reports/figures/e0_calibration.png),
[Gini by quarter](reports/figures/e0_gini_by_quarter.png) (per experiment in
`reports/figures/`).

## Data

Kaggle `wordsforthewise/lending-club`, file `accepted_2007_to_2018Q4.csv`.

| step | rows |
|---|---:|
| raw rows | 2,260,701 |
| valid `issue_d` (drops 2 footer rows + 31 empty rows) | 2,260,668 |
| finished outcome (target 0/1) | 1,348,099 |
| non-empty cleaned `desc` | 125,700 |

| split | issue months | rows | default rate |
|---|---|---:|---:|
| train | 2007-06 … 2013-07 | 88,697 | 15.64% |
| val | 2013-08 … 2013-11 | 17,145 | 15.07% |
| test | 2013-12 … 2014-03 (+85 stray loans to 2016-08) | 19,858 | 15.73% |

## Method and the decisions behind it

- **Target.** Fully Paid → 0; Charged Off / Default → 1. Current, Late and In Grace Period
  loans are dropped because their outcome is unknown. The "Does not meet the credit policy"
  cohort is kept with *both* outcomes. Keeping only its Charged Off rows would bias its
  default rate upward.
- **Leakage.** [leakage.py](src/features/leakage.py) holds a denylist of 39 post-origination
  columns, each with a reason, plus an allowlist of reviewed pre-origination columns. A
  column on neither list is dropped, and a test fails if any raw column is unclassified or
  any leakage column reaches a feature matrix.
- **Text cleaning.** Strips `Borrower added on MM/DD/YY >` and the older
  `<member_id> added on … >` edit markers, `<br>`/HTML tags and HTML entities. Only real
  tags are removed: borrowers write literal "< 40%", which a naive tag regex would delete.
- **Split.** Out-of-time on issue month, with boundaries snapped to whole months. `desc`
  disappears after March 2014: coverage is 36% of 2013 loans, 6.5% of 2014 loans and ~0%
  after that. So the test window is 4 months.
- **Tabular features (E0).** Allowlisted columns plus four ratios (credit history months,
  FICO midpoint, loan-to-income, installment-to-income). Excluded: `title`/`emp_title`
  (free text), `zip_code` (redlining proxy) and `issue_d` (a vintage feature cannot
  extrapolate). 32 bureau fields that are empty before 2015 are dropped, decided on train
  only.
- **Model.** CatBoost with identical settings and seed for every experiment
  ([base.yaml](configs/base.yaml)), early stopping on validation AUC, and no class weights
  (PD must stay calibrated).
- **Embeddings (E1).** `BAAI/bge-small-en-v1.5`, normalized, with a disk cache keyed by the
  hash of model + settings + text (duplicate texts are embedded once). PCA to 32 components,
  fit on train only. PCA rather than uncentered SVD because sentence embeddings share a
  large common direction.
- **LLM features (E2).** Any OpenAI-compatible endpoint, set up in [base.yaml](configs/base.yaml)
  and `.env`. The pydantic schema is from `CLAUDE.md`. The prompt defines what each score
  from 0 to 3 means. `employment_stability` = 0 means "not mentioned", so it is treated as a
  category, not a ranked score. Invalid JSON gets one retry with the validation error fed
  back, then becomes null. Results are cached by the hash of model + full prompt. Account
  and config errors (no credits, bad key, unknown model) stop the run instead of producing
  nulls. A fixed, split-stratified sample (`data/processed/llm_sample_ids.parquet`) is
  shared by E2 and E3.
- **Evaluation.** Gini/AUC/Brier with bootstrap CIs, a paired bootstrap for differences
  against E0, Gini by issue quarter, score PSI, reliability plots, exact TreeSHAP for LLM
  features (mean SHAP per feature value), and the 20 test loans where the models disagree
  most.

## Limitations (details in [results.md](reports/results.md#limitations))

- The text field ends in March 2014, so the test window is short and stability evidence rests
  on 2 quarters.
- Borrowers who wrote a description are a selected subset, and results do not carry over to
  applicants without text.
- `int_rate`/`grade` encode Lending Club's own risk model, which makes for a very strong
  baseline.
- Accepted loans only, with no reject inference.
- Each experiment is a single seed, and the CIs cover test sampling but not training
  randomness.
- One small LLM and one prompt. 39 of 125,700 answers are null, and in a hand review of a
  20-text pilot at least 4 outputs had a clearly wrong field. No larger audit was done.

## Reproduce

```bash
pip install -e ".[dev,embed,llm]"
kaggle datasets download -d wordsforthewise/lending-club -p data/raw --unzip

python -m scripts.prepare_data                               # ~1-2 min
python -m scripts.run_experiment --config configs/e0.yaml    # ~3 min CPU
python -m scripts.embed --config configs/e1.yaml             # 38 min on a 4-thread CPU
python -m scripts.run_experiment --config configs/e1.yaml
python -m scripts.run_experiment --config configs/e4.yaml

# LLM extraction: python -m scripts.package_code, upload dist/llm-credit-risk-lab-code.zip as
# a Kaggle Dataset, run notebooks/kaggle_e2_llm_extract.ipynb on a T4, unzip its output here.
# Or use any OpenAI-compatible endpoint:
cp .env.example .env                                         # then fill LLM_BASE_URL, LLM_API_KEY
python -m scripts.llm_extract --config configs/e2.yaml --n 20 --show --base-url <url>
python -m scripts.llm_extract --config configs/llm_baseten_glm.yaml --n 20 --show   # hosted alt.
python -m scripts.run_experiment --config configs/e2.yaml
python -m scripts.run_experiment --config configs/e3.yaml

python -m scripts.make_report                                # -> reports/results.md
```

If `llm.sample_size` is set below the full data, add `--llm-sample` to every
`run_experiment` call and to `make_report`, so E0–E4 are compared on the same loans.
[kaggle_e1_embeddings.ipynb](notebooks/kaggle_e1_embeddings.ipynb) runs prepare, embed, E0
and E1 on a Kaggle GPU; it has not been run on Kaggle yet.

## Showcase site

`site/` is a static Vite + React + Three.js page that presents the study. It never
hard-codes a result: `python -m scripts.export_site_data` writes `site/src/data/study.json`
from the run outputs, so the page and `reports/results.md` cannot disagree.

```bash
python -m scripts.export_site_data      # after any experiment run
cd site && npm install && npm run dev   # http://localhost:5173
npm run build                           # static bundle in site/dist
```

Add `?motion=on` to the URL to preview the animations on a machine whose OS has animation
effects turned off. Fill `site/src/content/profile.ts` with your name, repository URL and
email to enable the repository button and the contact form.

## Repo layout

```
configs/      base.yaml (shared settings) + e0..e4.yaml
src/data/     load, clean, target, split, prepare
src/features/ leakage lists, tabular, embeddings, llm_extract, assemble
src/models/   catboost_model, text_baseline (E4)
src/eval/     metrics (bootstrap, paired bootstrap, PSI, calibration), compare, shap, plots
scripts/      prepare_data, embed, llm_extract, run_experiment, make_report
tests/        leakage, split/cleaning, metrics, embeddings, LLM extraction, experiments
reports/      results.md, figures/, runs/<exp>/metrics.json
```

## Tests

```bash
pytest && ruff check .
```
