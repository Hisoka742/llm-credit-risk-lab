// Typed access to study.json, which `python -m scripts.export_site_data` writes from the
// repo's real outputs. Nothing on the page hard-codes a result.
import raw from "./study.json";

export type Interval = { value: number; ci_low: number; ci_high: number };
export type Diff = { diff: number; ci_low: number; ci_high: number; p_value_one_sided: number };

export type Experiment = {
  id: string;
  label: string;
  status: "done" | "pending";
  source?: string;
  n_features?: number | null;
  gini?: Interval;
  auc?: Interval;
  brier?: Interval;
  brier_skill?: number;
  mean_pd?: number;
  observed?: number;
  psi_train_test?: number;
  calibration?: { n: number; mean_pred: number; observed: number }[];
  by_quarter?: { period: string; n: number; gini: number; ci_low: number; ci_high: number }[];
  vs_e0?: { gini: Diff; brier: Diff; n: number };
  /** Share of total mean |SHAP| carried by the eight LLM features (E2, E3 only). */
  llm_shap_share?: number;
};

export type LlmReading = {
  loan_purpose_category: string;
  financial_stress: number;
  employment_stability: number;
  mentions_other_debts: boolean;
  mentions_job_loss_or_income_drop: boolean;
  mentions_medical_or_family_emergency: boolean;
  has_repayment_plan: boolean;
  text_quality: number;
};

export type Listing = {
  id: string;
  desc: string;
  year: number;
  grade: string;
  purpose: string;
  defaulted: boolean;
  split: string;
  llm: LlmReading;
  review: { verdict: "right" | "wrong" | "debatable"; note: string } | null;
};

export type Study = {
  funnel: { step: string; rows: number }[];
  coverage_by_year: { year: number; loans: number; with_desc: number; coverage: number }[];
  splits: {
    split: string;
    rows: number;
    defaults: number;
    first_month: string;
    last_month: string;
    share: number;
    default_rate: number;
  }[];
  leakage: { denied: { column: string; reason: string }[]; n_denied: number; n_allowed: number };
  experiments: Experiment[];
  terms: { raise: { term: string; coef: number }[]; lower: { term: string; coef: number }[] };
  word_weights: Record<string, number>;
  phrases: { text: string; n: number }[];
  listings: Listing[];
  pilot: {
    model: string;
    source: string;
    cost: {
      n: number;
      valid_rate: number;
      mean_prompt_tokens: number;
      mean_completion_tokens: number;
      accelerator_seconds_per_application: number;
    };
  };
  /** The full extraction run. Null until it has finished. */
  llm_run: {
    model: string;
    n: number;
    n_null: number;
    n_timed_calls: number;
    mean_prompt_tokens: number;
    mean_completion_tokens: number;
    gpu_seconds_per_application: number;
  } | null;
  embedding_cost: {
    model: string;
    device: string;
    mean_tokens: number;
    ms_per_application: number;
    n_texts: number;
    minutes: number;
  } | null;
  totals: {
    loans: number;
    defaults: number;
    default_rate: number;
    test_loans: number;
    unique_texts: number;
    n_bootstrap: number;
    tests?: number;
  };
};

export const study = raw as unknown as Study;

export const experiment = (id: string): Experiment | undefined =>
  study.experiments.find((e) => e.id === id);

const int = new Intl.NumberFormat("en-US");
export const fmtInt = (n: number): string => int.format(Math.round(n));
export const fmt = (n: number, digits = 3): string => n.toFixed(digits);
export const fmtSigned = (n: number, digits = 3): string =>
  `${n >= 0 ? "+" : "-"}${Math.abs(n).toFixed(digits)}`;
export const fmtPct = (n: number, digits = 1): string => `${(n * 100).toFixed(digits)}%`;
