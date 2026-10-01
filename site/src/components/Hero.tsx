import { useCalm } from "../lib/useCalm";
import { ArrowRight } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { experiment, fmtInt, fmtSigned, study } from "../data/study";
import { fieldCount } from "../lib/field";
import { useLang } from "../lib/i18n";
import { EASE_OUT } from "../lib/motion";
import { HeatText } from "./HeatText";
import { Magnetic } from "./Magnetic";

// The opening voice is a real description from the study (loan 200256). Its last sentence is
// quoted exactly as written, slip included.
const HERO_ID = "200256";
// The quote is evidence and stays in English. The Russian page adds this translation under it.
const HERO_QUOTE_RU = "«Заём с фиксированным ежемесячным платежом стал бы ответом на мои молитвы».";

// No regex lookbehind here: Safari before 16.4 rejects it at parse time, which would stop the
// whole page from loading on older iPhones.
function lastSentence(text: string): string {
  const parts = (text.match(/[^.!?]+[.!?]*/g) ?? []).map((x) => x.trim()).filter(Boolean);
  return parts[parts.length - 1] ?? text;
}

export function Hero() {
  const reduce = useCalm();
  const { t, ru } = useLang();
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

  const figure = diff ? (
    <span className="tnum whitespace-nowrap font-medium text-paper">
      {fmtSigned(diff.diff)} Gini, p = {diff.p_value_one_sided.toFixed(3)}
    </span>
  ) : null;

  return (
    <section id="top" className="relative z-10 flex min-h-[100dvh] flex-col justify-center">
      <div className="mx-auto w-full max-w-[1400px] px-5 pb-16 pt-24 md:px-10">
        <h1 className="sr-only">
          {t(
            "LLM Credit Risk Lab: do borrowers' own words improve a default model?",
            "LLM Credit Risk Lab: улучшают ли слова самих заёмщиков модель дефолта?",
          )}
        </h1>

        <blockquote
          lang="en"
          className="max-w-[18ch] font-display text-[clamp(2.6rem,7.2vw,6rem)] font-medium leading-[1.02] tracking-[-0.03em] md:max-w-[17ch]"
        >
          <p className="[text-wrap:balance]">
            <HeatText text={quote} resolve />
          </p>
        </blockquote>

        {ru && listing.id === HERO_ID && (
          <motion.p className="mt-5 max-w-[40ch] text-lg leading-snug text-paper/80" {...fade(after)}>
            {HERO_QUOTE_RU}
          </motion.p>
        )}

        <motion.p className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted" {...fade(after)}>
          <span>
            {t(
              `A Lending Club borrower, ${listing.year}. The loan was ${listing.defaulted ? "charged off" : "repaid"}.`,
              `Заёмщик Lending Club, ${listing.year} год. Кредит ${listing.defaulted ? "списан как безнадёжный" : "погашен"}.`,
            )}
          </span>
          <span className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-label={t("Colour key", "Обозначения цветов")}>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-warm" aria-hidden="true" />
              {t("word linked to default", "слово связано с дефолтом")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-cool" aria-hidden="true" />
              {t("linked to repayment", "связано с погашением")}
            </span>
          </span>
          <span className="basis-full">
            {dots === study.totals.loans
              ? t(
                  `Behind the text: one dot for each of the ${fmtInt(dots)} loans.`,
                  `За текстом: по одной точке на каждый из ${fmtInt(dots)} кредитов.`,
                )
              : t(
                  `Behind the text: a dot for ${fmtInt(dots)} of the ${fmtInt(study.totals.loans)} loans.`,
                  `За текстом: точки для ${fmtInt(dots)} из ${fmtInt(study.totals.loans)} кредитов.`,
                )}{" "}
            {t("The red ones defaulted.", "Красные — дефолты.")}
          </span>
        </motion.p>

        <motion.p
          className="mt-10 max-w-[46ch] text-lg leading-relaxed text-paper/90 md:text-xl"
          {...fade(after + 0.12)}
        >
          {ru ? (
            <>
              {fmtInt(study.totals.loans)} заёмщиков объяснили свою просьбу письменно. Чтение этих текстов
              сдвинуло модель дефолта{" "}
              {figure ? <>{allDone ? "не более чем на " : "на "}{figure}</> : "на величину, которая ещё измеряется"}.
            </>
          ) : (
            <>
              {fmtInt(study.totals.loans)} borrowers explained themselves in writing. Reading it moved a
              default model by{allDone ? " at most" : ""} {figure ?? "an amount still being measured"}.
            </>
          )}
        </motion.p>

        <motion.div className="mt-9 flex flex-wrap items-center gap-3" {...fade(after + 0.24)}>
          <Magnetic>
            <a href="#results" className="btn btn-primary">
              {t("Read the study", "К результатам")}
              <ArrowRight size={18} weight="bold" aria-hidden="true" />
            </a>
          </Magnetic>
          <a href="#method" className="btn btn-ghost">
            {t("See the method", "Как измеряли")}
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
