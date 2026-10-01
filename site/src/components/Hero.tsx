import { useCalm } from "../lib/useCalm";
import { ArrowRight } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { experiment, fmtInt, fmtSigned, study } from "../data/study";
import { fieldCount } from "../lib/field";
import { EASE_OUT } from "../lib/motion";
import { HeatText } from "./HeatText";
import { Magnetic } from "./Magnetic";

// The opening voice is a real description from the study (loan 200256). Its last sentence is
// quoted exactly as written, slip included.
const HERO_ID = "200256";

function lastSentence(text: string): string {
  const parts = text.split(/(?<=[.!?])\s+/).filter(Boolean);
  return parts[parts.length - 1] ?? text;
}

export function Hero() {
  const reduce = useCalm();
  const listing = study.listings.find((l) => l.id === HERO_ID) ?? study.listings[0];
  const quote = lastSentence(listing.desc);
  // The largest measured gain from any way of reading the text (E1, E2 or E3 against E0).
  const diffs = ["e1", "e2", "e3"].flatMap((id) => experiment(id)?.vs_e0?.gini ?? []);
  const diff = diffs.length ? diffs.reduce((a, b) => (b.diff > a.diff ? b : a)) : undefined;
  const allDone = diffs.length === 3;
  const dots = fieldCount();
  const words = quote.split(/\s+/).length;
  const after = reduce ? 0 : 0.25 + words * 0.055 + 0.5;

  const fade = (delay: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 16 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, delay, ease: EASE_OUT },
        };

  return (
    <section id="top" className="relative z-10 flex min-h-[100dvh] flex-col justify-center">
      <div className="mx-auto w-full max-w-[1400px] px-5 pb-16 pt-24 md:px-10">
        <h1 className="sr-only">
          LLM Credit Risk Lab: do borrowers' own words improve a default model?
        </h1>

        <blockquote className="max-w-[18ch] font-display text-[clamp(2.6rem,7.2vw,6rem)] font-medium leading-[1.02] tracking-[-0.03em] md:max-w-[17ch]">
          <p className="[text-wrap:balance]">
            <HeatText text={quote} resolve />
          </p>
        </blockquote>

        <motion.p className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted" {...fade(after)}>
          <span>
            A Lending Club borrower, {listing.year}. The loan was{" "}
            {listing.defaulted ? "charged off" : "repaid"}.
          </span>
          <span className="flex items-center gap-4" aria-label="Colour key">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-warm" aria-hidden="true" />
              word linked to default
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-cool" aria-hidden="true" />
              linked to repayment
            </span>
          </span>
          <span className="basis-full">
            {dots === study.totals.loans
              ? `Behind the text: one dot for each of the ${fmtInt(dots)} loans.`
              : `Behind the text: a dot for ${fmtInt(dots)} of the ${fmtInt(study.totals.loans)} loans.`}{" "}
            The red ones defaulted.
          </span>
        </motion.p>

        <motion.p
          className="mt-10 max-w-[46ch] text-lg leading-relaxed text-paper/90 md:text-xl"
          {...fade(after + 0.12)}
        >
          {fmtInt(study.totals.loans)} borrowers explained themselves in writing. Reading it moved a
          default model by{allDone ? " at most" : ""}{" "}
          {diff ? (
            <span className="tnum whitespace-nowrap font-medium text-paper">
              {fmtSigned(diff.diff)} Gini, p = {diff.p_value_one_sided.toFixed(3)}
            </span>
          ) : (
            "an amount still being measured"
          )}
          .
        </motion.p>

        <motion.div className="mt-9 flex flex-wrap items-center gap-3" {...fade(after + 0.24)}>
          <Magnetic>
            <a href="#results" className="btn btn-primary">
              Read the study
              <ArrowRight size={18} weight="bold" aria-hidden="true" />
            </a>
          </Magnetic>
          <a href="#method" className="btn btn-ghost">
            See the method
          </a>
        </motion.div>
      </div>

      {/* The field fades into the page ground so the next section starts clean. */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-ink/70"
        aria-hidden="true"
      />
    </section>
  );
}
