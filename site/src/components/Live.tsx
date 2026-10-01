import { ArrowCounterClockwise, CircleNotch } from "@phosphor-icons/react";
import { type FormEvent, useEffect, useId, useState } from "react";
import { fmtInt, fmtPct } from "../data/study";
import { Reveal } from "./Reveal";

// The live demo needs the API from `python -m scripts.serve`. In development the Vite server
// proxies /api to it. A production build only talks to an API when VITE_API_URL is set, so the
// static site never shows a demo that cannot answer.
const API: string = import.meta.env.VITE_API_URL ?? "";
const ENABLED = import.meta.env.DEV || Boolean(API);

type Reading = Record<string, string | number | boolean | null>;

type Profile = {
  id: string;
  desc: string;
  issued: string;
  grade: string;
  int_rate: number;
  loan_amnt: number;
  annual_inc: number;
  purpose: string;
  defaulted: boolean;
  pd_no_text: number;
  pd_original_text: number;
  original_reading: Reading;
};

type Health = { reader: string; trained_on: string; max_text_chars: number };

type Analysis = {
  profile_id: string;
  reader: string;
  reading: Reading | null;
  error: string | null;
  cached: boolean;
  latency_s: number;
  prompt_tokens: number;
  completion_tokens: number;
  pd_your_text: number;
  contributions: { field: string; log_odds: number }[];
};

const LABELS: Record<string, string> = {
  loan_purpose_category: "Purpose",
  financial_stress: "Financial stress (0 to 3)",
  employment_stability: "Employment stability (0 to 3)",
  mentions_other_debts: "Mentions other debts",
  mentions_job_loss_or_income_drop: "Mentions job loss or income drop",
  mentions_medical_or_family_emergency: "Mentions medical or family emergency",
  has_repayment_plan: "Has a repayment plan",
  text_quality: "Text quality (0 to 3)",
};

const show = (v: string | number | boolean | null | undefined): string =>
  v === null || v === undefined
    ? "none"
    : typeof v === "boolean"
      ? v ? "yes" : "no"
      : String(v).replace(/_/g, " ");

const shortName = (model: string) => model.split("/").pop() ?? model;

function PdFigure({ label, value, strong }: { label: string; value: number | null; strong?: boolean }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`tnum mt-1 font-display text-2xl font-medium sm:text-3xl tracking-[-0.02em] ${strong ? "text-paper" : "text-paper/70"}`}>
        {value === null ? <span className="text-faint">...</span> : fmtPct(value)}
      </dd>
    </div>
  );
}

export function Live() {
  const [health, setHealth] = useState<Health | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [text, setText] = useState("");
  const [result, setResult] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textId = useId();

  useEffect(() => {
    if (!ENABLED) return;
    const ctl = new AbortController();
    Promise.all([
      fetch(`${API}/api/health`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject())),
      fetch(`${API}/api/profiles`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject())),
    ])
      .then(([h, p]: [Health, Profile[]]) => {
        if (!p.length) return;
        setHealth(h);
        setProfiles(p);
        setSelected(p[0].id);
        setText(p[0].desc);
      })
      .catch(() => undefined); // API not running: the section stays hidden
    return () => ctl.abort();
  }, []);

  const profile = profiles.find((p) => p.id === selected);
  if (!health || !profile) return null;

  const pick = (p: Profile) => {
    setSelected(p.id);
    setText(p.desc);
    setResult(null);
    setError(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || !text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profile.id, text }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail = typeof body.detail === "string" ? body.detail : "The request was rejected.";
        throw new Error(detail);
      }
      setResult(body as Analysis);
    } catch (err) {
      setResult(null);
      setError(err instanceof TypeError ? "The demo server is not reachable." : (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const mine = result && result.profile_id === profile.id ? result : null;
  const delta = mine ? mine.pd_your_text - profile.pd_original_text : null;
  const tooLong = text.length > health.max_text_chars;
  const sameReader = shortName(health.reader) === shortName(health.trained_on);

  return (
    <section id="live" className="relative z-10 bg-ink/65 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            Same borrower, your words
          </h2>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-muted">
            Pick a real loan from the test set and rewrite its description. {shortName(health.reader)}{" "}
            reads your text now, and the trained model scores the same borrower again. Income, rate,
            credit history and every other number stay fixed.
          </p>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
          <form onSubmit={submit} className="min-w-0">
            <fieldset>
              <legend className="text-sm text-muted">Borrower</legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {profiles.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => pick(p)}
                    aria-pressed={p.id === profile.id}
                    className={`tnum rounded-full border px-3.5 py-2 text-sm transition-colors duration-150 ${
                      p.id === profile.id
                        ? "border-paper bg-paper text-ink"
                        : "border-line text-muted hover:border-paper/50 hover:text-paper"
                    }`}
                  >
                    Grade {p.grade}, ${fmtInt(p.loan_amnt / 1000)}k
                  </button>
                ))}
              </div>
            </fieldset>

            <p className="tnum mt-5 text-sm leading-relaxed text-muted">
              Issued {profile.issued}. ${fmtInt(profile.loan_amnt)} at {profile.int_rate.toFixed(2)}%, income $
              {fmtInt(profile.annual_inc)}, stated purpose {profile.purpose.replace(/_/g, " ")}. This loan was{" "}
              <span className={profile.defaulted ? "text-warm" : "text-paper"}>
                {profile.defaulted ? "charged off" : "repaid"}
              </span>
              .
            </p>

            <label htmlFor={textId} className="mt-7 block text-sm font-medium">
              Description
            </label>
            <textarea
              id={textId}
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              spellCheck
              aria-describedby={`${textId}-count`}
              className="mt-2 w-full resize-y rounded-2xl border border-line bg-ink-2/80 p-4 leading-relaxed text-paper placeholder:text-faint"
              placeholder="Write what this borrower might have said."
            />
            <p id={`${textId}-count`} className={`tnum mt-1.5 text-xs ${tooLong ? "text-paper" : "text-faint"}`}>
              {fmtInt(text.length)} of {fmtInt(health.max_text_chars)} characters
              {tooLong ? ". Shorten the text to send it." : ""}
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button type="submit" className="btn btn-primary" disabled={busy || tooLong || !text.trim()} aria-busy={busy}>
                {busy && <CircleNotch size={18} weight="bold" className="animate-spin" aria-hidden="true" />}
                {busy ? "Reading" : "Read it and score"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => pick(profile)} disabled={busy || text === profile.desc}>
                <ArrowCounterClockwise size={18} aria-hidden="true" />
                Original text
              </button>
            </div>
            {error && (
              <p role="alert" className="mt-4 max-w-[56ch] text-sm leading-relaxed text-paper">
                {error}
              </p>
            )}
          </form>

          <div className="glass min-w-0 p-6 md:p-8" aria-live="polite">
            <dl className="grid grid-cols-3 gap-3">
              <PdFigure label="No text" value={profile.pd_no_text} />
              <PdFigure label="Original text" value={profile.pd_original_text} />
              <PdFigure label="Your text" value={mine ? mine.pd_your_text : null} strong />
            </dl>
            <p className="tnum mt-4 min-h-[3rem] text-sm leading-relaxed text-muted">
              {delta === null
                ? "Predicted probability of default. Send a description to fill the third figure."
                : Math.abs(delta) < 0.0005
                  ? "Your text leaves the predicted probability of default unchanged."
                  : `Your text moves the predicted probability of default ${delta > 0 ? "up" : "down"} by ${(Math.abs(delta) * 100).toFixed(1)} points against the original text.`}
            </p>

            <table className="mt-6 w-full table-fixed border-t border-line text-sm [overflow-wrap:anywhere]">
              <colgroup>
                <col className="w-[40%]" />
                <col className="w-[22%]" />
                <col className="w-[22%]" />
                <col className="w-[16%]" />
              </colgroup>
              <thead className="text-left text-muted">
                <tr>
                  <th scope="col" className="py-3 pr-3 font-normal">Extracted field</th>
                  <th scope="col" className="py-3 pr-3 font-normal">Original</th>
                  <th scope="col" className="py-3 pr-3 font-normal">Yours</th>
                  <th scope="col" className="py-3 text-right font-normal">Effect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line border-y border-line">
                {Object.keys(LABELS).map((f) => {
                  const before = show(profile.original_reading[f]);
                  const after = mine ? show(mine.reading?.[f]) : "";
                  const c = mine?.contributions.find((x) => x.field === f)?.log_odds;
                  return (
                    <tr key={f}>
                      <th scope="row" className="py-2.5 pr-3 text-left font-normal text-muted">{LABELS[f]}</th>
                      <td className="tnum py-2.5 pr-3 text-paper/70">{before}</td>
                      <td className={`tnum py-2.5 pr-3 ${mine && after !== before ? "font-medium text-paper" : "text-paper/70"}`}>
                        {after}
                      </td>
                      <td className={`tnum py-2.5 text-right ${c === undefined || Math.abs(c) < 0.005 ? "text-faint" : c > 0 ? "text-warm" : "text-cool"}`}>
                        {c === undefined ? "" : `${c >= 0 ? "+" : "-"}${Math.abs(c).toFixed(2)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {mine?.reading === null && (
              <p className="mt-4 text-sm leading-relaxed text-paper">
                The model's answer did not match the schema twice, so the text features were scored as missing.
              </p>
            )}
            <p className="mt-5 text-sm leading-relaxed text-muted">
              Effect is each field's push on the score in log-odds: positive raises the predicted risk.
              {mine
                ? ` Read by ${shortName(mine.reader)} in ${mine.latency_s.toFixed(1)} s, ${mine.prompt_tokens} tokens in and ${mine.completion_tokens} out${mine.cached ? " (answer reused from cache)" : ""}.`
                : ""}
            </p>
            {!sameReader && (
              <p className="mt-3 text-sm leading-relaxed text-muted">
                The scoring model learned from {shortName(health.trained_on)}'s readings, and{" "}
                {shortName(health.reader)} is a different reader. Treat the change as an illustration of
                the mechanism, not as a validated prediction.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
