# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vite + React + Three.js (React Three Fiber) for the showcase site, in `site/`, built as a static bundle deployable to GitHub Pages or Vercel (deploy target not yet chosen). The research code itself is Python (see README.md).

## Users

A hiring team at a bank risk-modeling or LLM-research group (hiring manager, senior modeler, interviewer) evaluating the author. They arrive from a CV, message or portfolio link, skim for a few minutes, and are deciding whether this person measures things correctly and can defend every modeling decision in an interview.

## Product Purpose

LLM Credit Risk Lab is a reproducible study of whether features derived from borrowers' free-text loan descriptions (sentence embeddings, and structured JSON extracted by an LLM) improve a classical CatBoost probability-of-default model on Lending Club data, measured out-of-time with bootstrap confidence intervals. The showcase site presents that study, its method, results and limitations. Success: the visitor leaves convinced of the author's rigor and opens the repository or makes contact.

## Positioning

An honest, measured answer rather than a hype result: leakage controlled by an allowlist and denylist enforced by tests, a month-snapped out-of-time split, paired bootstrap against the baseline, a random-feature placebo that exposed the noise floor, calibration and PSI, and a cost table in real units. A small or null effect, reported correctly, is the point.

## Operating Context

Read on desktop during a hiring review, often alongside the GitHub repository and README; sometimes on a phone from a message link. The numbers must be checkable against `reports/results.md` and `reports/runs/*/metrics.json`.

## Capabilities and Constraints

- Finished: data pipeline (2,260,701 raw rows -> 125,700 loans with descriptions), E0 tabular baseline, E1 embeddings, E4 TF-IDF text-only baseline, report generator.
- In progress: E2/E3 LLM-feature experiments. Extraction with Qwen2.5-7B-Instruct (AWQ, vLLM, Kaggle T4) is partially complete; the site shows them as in progress with the real 20-description pilot, and fills numbers from metrics.json when available.
- Every number shown must come from the repository's outputs. No invented results.
- The project was built with an AI coding agent (Claude Code); the workflow may appear as one chapter, not the lead.

## Evidence on Hand

- `reports/results.md`, `reports/runs/{e0,e1,e4}/metrics.json`, `reports/figures/*.png` (calibration, Gini by quarter).
- E0 test Gini 0.4166 [0.3982, 0.4354]; E1 0.4209 [0.4029, 0.4403], paired diff +0.0043 [-0.0017, +0.0102], p = 0.079; E4 0.1893 [0.1668, 0.2104].
- Real LLM pilot outputs (20 descriptions, Qwen2.5-7B and GLM-5.3-Flash), recorded in the session and partly in `data/processed/llm_features/*.n20.parquet`.
- Absent and not to be fabricated: author name and bio, GitHub URL, contact details, testimonials, employer logos, final E2/E3 numbers.

## Product Principles

- Measured over impressive: every claim carries its interval and its test.
- Show the machinery: leakage lists, split boundaries, placebo, cost, not just headline scores.
- Limitations are content, stated as plainly as results.
- Defensible in an interview: each design decision has a stated reason.

## Accessibility & Inclusion

Readable at desktop and phone widths, respects reduced-motion preferences, and keeps all numbers available as text, not only in charts or 3D.
