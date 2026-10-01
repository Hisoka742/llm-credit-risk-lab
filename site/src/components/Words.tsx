import { useCalm } from "../lib/useCalm";
import { motion } from "motion/react";
import { experiment, fmt, fmtInt, study } from "../data/study";
import { EASE_OUT } from "../lib/motion";
import { Reveal } from "./Reveal";

type Term = { term: string; coef: number };

function TermList({ terms, tone, align }: { terms: Term[]; tone: "warm" | "cool"; align: "left" | "right" }) {
  const reduce = useCalm();
  const max = Math.max(...terms.map((t) => Math.abs(t.coef)), 0.001);
  return (
    <ul className="space-y-2.5">
      {terms.map((t, i) => (
        <li key={t.term} className={`flex items-center gap-3 ${align === "right" ? "md:flex-row-reverse" : ""}`}>
          <span className={`w-36 shrink-0 text-[0.95rem] ${align === "right" ? "md:text-right" : ""}`}>{t.term}</span>
          <span className={`flex flex-1 ${align === "right" ? "md:justify-end" : ""}`}>
            <motion.span
              className={`h-1.5 rounded-full ${tone === "warm" ? "bg-warm" : "bg-cool"} ${
                align === "right" ? "origin-left md:origin-right" : "origin-left"
              }`}
              style={{ width: `${(Math.abs(t.coef) / max) * 100}%` }}
              initial={reduce ? false : { scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: i * 0.035, ease: EASE_OUT }}
            />
          </span>
        </li>
      ))}
    </ul>
  );
}

/** One strip of the phrases borrowers typed most often. The page's only marquee. */
function Phrases() {
  const items = study.phrases.slice(0, 16);
  const strip = (hidden: boolean) => (
    <ul className="flex shrink-0 items-center gap-10 pr-10" aria-hidden={hidden || undefined}>
      {items.map((p) => (
        <li key={p.text} className="flex items-baseline gap-3 whitespace-nowrap">
          <span className="font-display text-3xl font-medium tracking-[-0.02em] md:text-5xl">{p.text}</span>
          <span className="tnum text-sm text-muted">{fmtInt(p.n)}</span>
        </li>
      ))}
    </ul>
  );
  return (
    <div className="marquee overflow-hidden border-y border-line py-7">
      <div className="marquee-track flex w-max">
        {strip(false)}
        {strip(true)}
      </div>
    </div>
  );
}

export function Words() {
  const e4 = experiment("e4");
  return (
    <section id="words" className="relative z-10 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[20ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            The words do carry signal. Just not much that is new.
          </h2>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-muted">
            A model that sees only the text reaches a Gini of{" "}
            <span className="tnum text-paper">{e4?.gini ? fmt(e4.gini.value) : "an unknown value"}</span>.
            Borrowers who need help with bills or fund a business default more. Those refinancing
            cards at a better rate default less. The tabular purpose field already knows most of
            this.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-12 md:grid-cols-2 md:gap-16">
          <div>
            <h3 className="mb-6 text-sm font-medium text-warm">Linked to default</h3>
            <TermList terms={study.terms.raise} tone="warm" align="right" />
          </div>
          <div>
            <h3 className="mb-6 text-sm font-medium text-cool">Linked to repayment</h3>
            <TermList terms={study.terms.lower} tone="cool" align="left" />
          </div>
        </div>
        <p className="mt-10 max-w-[62ch] text-sm leading-relaxed text-muted">
          Bar length is the term's weight in the text-only model. Several of the strongest terms are
          filler words: the signal in this text is real but weak and diffuse.
        </p>
      </div>

      <div className="mt-20">
        <div className="mx-auto mb-8 max-w-[1400px] px-5 md:px-10">
          <Reveal>
            <h3 className="max-w-[26ch] font-display text-2xl font-medium leading-tight tracking-[-0.015em] md:text-3xl">
              And many borrowers wrote almost nothing
            </h3>
          </Reveal>
        </div>
        <Phrases />
      </div>
    </section>
  );
}
