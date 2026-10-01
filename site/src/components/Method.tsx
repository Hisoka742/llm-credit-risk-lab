import { useCalm } from "../lib/useCalm";
import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { type PointerEvent, type ReactNode, useState } from "react";
import { experiment, fmtInt, fmtPct, fmtSigned, study } from "../data/study";
import { EASE_OUT } from "../lib/motion";
import { Reveal } from "./Reveal";

/**
 * Bento cell: frosted card that tilts a few degrees toward the cursor (mouse only) and
 * enters with a small stagger. Tilt uses motion values, so it never re-renders React.
 */
function Cell({ children, className = "", index }: { children: ReactNode; className?: string; index: number }) {
  const reduce = useCalm();
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const rx = useSpring(useTransform(py, [-0.5, 0.5], [3.2, -3.2]), { stiffness: 160, damping: 18 });
  const ry = useSpring(useTransform(px, [-0.5, 0.5], [-3.2, 3.2]), { stiffness: 160, damping: 18 });

  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (reduce || e.pointerType !== "mouse") return;
    const r = e.currentTarget.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width - 0.5);
    py.set((e.clientY - r.top) / r.height - 0.5);
  };
  const reset = () => {
    px.set(0);
    py.set(0);
  };

  return (
    <motion.div
      className={`[perspective:1200px] ${className}`}
      initial={reduce ? false : { opacity: 0, y: 28, scale: 0.97 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.7, delay: index * 0.06, ease: EASE_OUT }}
    >
      <motion.div
        className="glass h-full p-6 md:p-8"
        style={{ rotateX: rx, rotateY: ry, transformStyle: "preserve-3d" }}
        onPointerMove={onMove}
        onPointerLeave={reset}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

const H3 = "font-display text-2xl font-medium leading-tight tracking-[-0.015em] md:text-[1.75rem]";
const BODY = "mt-3 max-w-[52ch] text-[0.975rem] leading-relaxed text-muted";

function Leakage() {
  const { denied, n_denied, n_allowed } = study.leakage;
  const [active, setActive] = useState(denied.find((d) => d.column === "recoveries") ?? denied[0]);

  return (
    <div className="flex h-full flex-col">
      <h3 className={H3}>{n_denied} columns never reach the model</h3>
      <p className={BODY}>
        Anything known only after a loan is issued would predict default almost perfectly. Those
        columns are denied by name, {n_allowed} reviewed columns are allowed, and anything on
        neither list is dropped. A test fails if either rule breaks.
      </p>
      {/* Column names are code identifiers, so they are set in the mono face. */}
      <ul className="mb-6 mt-8 flex flex-wrap gap-x-4 gap-y-2.5 font-mono text-[14px] leading-snug" aria-label="Denied columns">
        {denied.map((d) => (
          <li key={d.column} className="max-w-full">
            <button
              type="button"
              onPointerEnter={() => setActive(d)}
              onFocus={() => setActive(d)}
              onClick={() => setActive(d)}
              aria-pressed={active.column === d.column}
              className={`max-w-full rounded px-0.5 text-left line-through decoration-paper/35 [overflow-wrap:anywhere] decoration-1 transition-colors duration-150 ${
                active.column === d.column ? "text-paper" : "text-muted hover:text-paper"
              }`}
            >
              {d.column}
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-auto border-t border-line pt-5 text-[0.975rem] leading-relaxed" aria-live="polite">
        <span className="font-mono text-[14px] text-paper">{active.column}</span>
        <span className="text-muted">: {active.reason}</span>
      </p>
    </div>
  );
}

function Funnel() {
  const calm = useCalm();
  const pick = (prefix: string) => study.funnel.find((f) => f.step.startsWith(prefix))?.rows ?? 0;
  const rows = [
    { label: "loans in the raw file", n: pick("raw") },
    { label: "with a finished outcome", n: pick("finished") },
    { label: "where the borrower wrote something", n: pick("unique") },
  ];
  const max = rows[0].n || 1;
  return (
    <>
      <h3 className={H3}>From 2.26 million loans to the ones with a voice</h3>
      <ul className="mt-6 space-y-4">
        {rows.map((r, i) => (
          <li key={r.label}>
            <p className="flex items-baseline justify-between gap-4 text-sm">
              <span className="text-muted">{r.label}</span>
              <span className="tnum font-medium">{fmtInt(r.n)}</span>
            </p>
            <motion.div
              className="mt-2 h-1.5 origin-left rounded-full bg-paper"
              style={{ width: `${Math.max(1.5, (r.n / max) * 100)}%`, opacity: 1 - i * 0.22 }}
              initial={calm ? false : { scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: 0.15 + i * 0.12, ease: EASE_OUT }}
            />
          </li>
        ))}
      </ul>
    </>
  );
}

function Coverage() {
  const calm = useCalm();
  const years = study.coverage_by_year;
  return (
    <>
      <h3 className={H3}>The text field disappears in 2014</h3>
      <div className="mt-6 flex h-32 items-end gap-1.5" role="img" aria-label="Share of loans with a description, by issue year">
        {years.map((y, i) => (
          <div key={y.year} className="flex h-full flex-1 flex-col justify-end">
            <motion.div
              className="origin-bottom rounded-t-[3px] bg-paper"
              style={{ height: `${Math.max(1, y.coverage * 100)}%`, opacity: y.coverage > 0.02 ? 0.9 : 0.25 }}
              initial={calm ? false : { scaleY: 0 }}
              whileInView={{ scaleY: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 + i * 0.04, ease: EASE_OUT }}
            />
          </div>
        ))}
      </div>
      <div className="tnum mt-2 flex gap-1.5 text-[11px] text-faint" aria-hidden="true">
        {years.map((y) => (
          <span key={y.year} className="flex-1 text-center">
            {String(y.year).slice(2)}
          </span>
        ))}
      </div>
      <p className={BODY}>
        {fmtPct(years.find((y) => y.year === 2013)?.coverage ?? 0, 0)} of 2013 loans carry a
        description, {fmtPct(years.find((y) => y.year === 2014)?.coverage ?? 0, 1)} of 2014 loans,
        none after. The study can only speak about that window.
      </p>
    </>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2013-07" -> "Jul 2013" */
const fmtMonth = (ym: string): string => `${MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;

function Split() {
  const calm = useCalm();
  const tone = ["bg-paper/30", "bg-paper/60", "bg-paper"];
  return (
    <>
      <h3 className={H3}>Train on the past, test on the future</h3>
      <div className="mt-6 flex h-3 gap-1 overflow-hidden rounded-full" aria-hidden="true">
        {study.splits.map((s, i) => (
          <motion.div
            key={s.split}
            className={`origin-left ${tone[i]}`}
            style={{ width: `${s.share * 100}%` }}
            initial={calm ? false : { scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.15 + i * 0.18, ease: EASE_OUT }}
          />
        ))}
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
        {study.splits.map((s) => (
          <div key={s.split}>
            <dt className="font-medium capitalize">{s.split === "val" ? "Validation" : s.split}</dt>
            <dd className="tnum mt-1 leading-snug text-muted">
              {fmtInt(s.rows)} loans
              <br />
              {s.split === "test"
                ? `from ${fmtMonth(s.first_month)}`
                : `${fmtMonth(s.first_month)} to ${fmtMonth(s.last_month)}`}
            </dd>
          </div>
        ))}
      </dl>
      <p className={BODY}>
        Split by issue month, never at random, and no month sits in two splits. Early stopping
        uses validation only.
      </p>
    </>
  );
}

function Bootstrap() {
  const d = experiment("e1")?.vs_e0?.gini;
  return (
    <>
      <h3 className={H3}>Every difference is paired</h3>
      <p className={BODY}>
        Both models are scored on the same {fmtInt(study.totals.n_bootstrap)} resampled test sets,
        so shared sampling noise cancels and only the difference remains.
      </p>
      {d && (
        <p className="tnum mt-5 text-sm text-paper/85">
          Embeddings vs baseline: {fmtSigned(d.diff, 4)} Gini, interval {fmtSigned(d.ci_low, 4)} to{" "}
          {fmtSigned(d.ci_high, 4)}.
        </p>
      )}
    </>
  );
}

function Tests() {
  return (
    <>
      <p className="tnum font-display text-6xl font-medium leading-none tracking-[-0.03em]">
        {study.totals.tests ?? ""}
      </p>
      <h3 className="mt-3 font-display text-xl font-medium">automated tests</h3>
      <p className={BODY}>
        Including one that fails the build if a leakage column reaches the feature matrix.
      </p>
    </>
  );
}

export function Method() {
  return (
    <section id="method" className="relative z-10 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            How it was measured
          </h2>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-12">
          <Cell index={0} className="md:col-span-2 lg:col-span-7 lg:row-span-2">
            <Leakage />
          </Cell>
          <Cell index={1} className="lg:col-span-5">
            <Funnel />
          </Cell>
          <Cell index={2} className="lg:col-span-5">
            <Coverage />
          </Cell>
          <Cell index={3} className="lg:col-span-5">
            <Split />
          </Cell>
          <Cell index={4} className="lg:col-span-4">
            <Bootstrap />
          </Cell>
          <Cell index={5} className="md:col-span-2 lg:col-span-3">
            <Tests />
          </Cell>
        </div>
      </div>
    </section>
  );
}
