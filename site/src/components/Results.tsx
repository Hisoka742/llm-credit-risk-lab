import { useCalm } from "../lib/useCalm";
import { motion } from "motion/react";
import { EXPERIMENT_LABEL_RU } from "../content/ru";
import { type Experiment, experiment, fmt, fmtInt, fmtPct, fmtSigned, study } from "../data/study";
import { useLang } from "../lib/i18n";
import { EASE_OUT } from "../lib/motion";
import { Reveal } from "./Reveal";

// Gini axis for the interval chart. Wide enough for the text-only model and the baseline.
const X_MIN = 0.1;
const X_MAX = 0.5;
const TICKS = [0.1, 0.2, 0.3, 0.4, 0.5];
const pos = (v: number) => `${((v - X_MIN) / (X_MAX - X_MIN)) * 100}%`;

function IntervalRow({ e, index }: { e: Experiment; index: number }) {
  const reduce = useCalm();
  const { t, ru } = useLang();
  const g = e.gini;
  return (
    <li className="grid grid-cols-1 items-center gap-x-6 gap-y-2 py-5 md:grid-cols-[19rem_1fr_13rem]">
      <p>
        <span className="tnum text-lg font-bold">{e.id.toUpperCase()}</span>
        <span className="ml-3 text-muted">{(ru && EXPERIMENT_LABEL_RU[e.id]) || e.label}</span>
      </p>

      <div className="relative h-8" aria-hidden="true">
        {TICKS.map((t) => (
          <span key={t} className="absolute top-0 h-full w-px bg-line" style={{ left: pos(t) }} />
        ))}
        {g ? (
          <>
            <motion.span
              className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-paper"
              style={{ left: pos(g.ci_low), right: `calc(100% - ${pos(g.ci_high)})` }}
              initial={reduce ? false : { scaleX: 0, opacity: 0 }}
              whileInView={{ scaleX: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.15 + index * 0.1, ease: EASE_OUT }}
            />
            <motion.span
              className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink bg-paper"
              style={{ left: pos(g.value) }}
              initial={reduce ? false : { scale: 0.6, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.5 + index * 0.1, ease: EASE_OUT }}
            />
          </>
        ) : (
          <span
            className="absolute top-1/2 h-px -translate-y-1/2 border-t border-dashed border-faint"
            style={{ left: pos(0.36), right: `calc(100% - ${pos(0.48)})` }}
          />
        )}
      </div>

      {g ? (
        <p className="tnum text-sm">
          <span className="text-base font-medium">{fmt(g.value)}</span>
          <span className="ml-2 text-muted">
            {t(`${fmt(g.ci_low)} to ${fmt(g.ci_high)}`, `от ${fmt(g.ci_low)} до ${fmt(g.ci_high)}`)}
          </span>
        </p>
      ) : (
        <p className="text-sm text-muted">{t("Extraction in progress", "Извлечение ещё идёт")}</p>
      )}
    </li>
  );
}

// Paired differences against the baseline, all on one axis so they can be compared.
const D_MIN = -0.02;
const D_MAX = 0.02;
const dpos = (v: number) => `${((v - D_MIN) / (D_MAX - D_MIN)) * 100}%`;
const READINGS = [
  { id: "e1", en: "Embeddings", ru: "Эмбеддинги" },
  { id: "e2", en: "LLM features", ru: "Признаки LLM" },
  { id: "e3", en: "Both together", ru: "Оба вместе" },
];

function Difference() {
  const reduce = useCalm();
  const { t, ru } = useLang();
  const rows = READINGS.flatMap((r) => {
    const vs = experiment(r.id)?.vs_e0;
    return vs ? [{ id: r.id, name: ru ? r.ru : r.en, d: vs.gini, n: vs.n }] : [];
  });
  if (!rows.length) return null;
  const significant = rows.filter((r) => r.d.ci_low > 0);
  const e2 = experiment("e2");
  const complete = rows.length === READINGS.length;

  return (
    <div className="mt-16 grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-end">
      <div>
        <h3 className="font-display text-[clamp(1.6rem,2.8vw,2.4rem)] font-medium leading-[1.1] tracking-[-0.02em]">
          {significant.length
            ? t(
                `${significant.map((r) => r.name).join(" and ")}: the interval excludes zero.`,
                `${significant.map((r) => r.name).join(" и ")}: интервал не включает ноль.`,
              )
            : complete
              ? t(
                  "Three ways to read the text. Every interval includes zero.",
                  "Три способа прочитать текст. Каждый интервал включает ноль.",
                )
              : t(
                  "Embeddings help a little. The interval still includes zero.",
                  "Эмбеддинги немного помогают. Интервал всё ещё включает ноль.",
                )}
        </h3>
        <p className="mt-4 max-w-[56ch] leading-relaxed text-muted">
          {rows.map((r, i) => (
            <span key={r.id}>
              {i > 0 ? ", " : ""}
              {r.name} {t("change test Gini by", "меняют Gini на тесте на")}{" "}
              <span className="tnum text-paper">{fmtSigned(r.d.diff, 4)}</span> (p ={" "}
              <span className="tnum text-paper">{r.d.p_value_one_sided.toFixed(3)}</span>)
            </span>
          ))}
          .{" "}
          {t(
            "Each model was trained once, with one seed, and gains of a few thousandths are the size that training noise alone can produce.",
            "Каждая модель обучена один раз, с одним seed, а прирост в несколько тысячных — это масштаб, который даёт один только шум обучения.",
          )}
          {e2?.llm_shap_share !== undefined
            ? t(
                ` The model does use the language-model features: they carry ${fmtPct(e2.llm_shap_share)} of its total SHAP weight. That did not turn into better ranking.`,
                ` Признаки языковой модели модель действительно использует: на них приходится ${fmtPct(e2.llm_shap_share)} суммарного веса SHAP. В лучшее ранжирование это не превратилось.`,
              )
            : ""}
        </p>
      </div>

      <figure>
        <ul className="space-y-1" aria-hidden="true">
          {rows.map((r, i) => (
            <li key={r.id} className="grid grid-cols-[7.5rem_1fr] items-center gap-3">
              <span className="text-sm text-muted">{r.name}</span>
              <div className="relative h-10">
                <span className="absolute inset-y-0 w-px bg-paper/60" style={{ left: dpos(0) }} />
                <motion.span
                  className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-paper"
                  style={{ left: dpos(r.d.ci_low), right: `calc(100% - ${dpos(r.d.ci_high)})` }}
                  initial={reduce ? false : { scaleX: 0 }}
                  whileInView={{ scaleX: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.2 + i * 0.1, ease: EASE_OUT }}
                />
                <span
                  className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink bg-paper"
                  style={{ left: dpos(r.d.diff) }}
                />
              </div>
            </li>
          ))}
        </ul>
        <div className="tnum relative ml-[8.25rem] h-5 text-xs text-muted" aria-hidden="true">
          <span className="absolute left-0">-0.02</span>
          <span className="absolute -translate-x-1/2 text-paper" style={{ left: dpos(0) }}>0</span>
          <span className="absolute right-0">+0.02</span>
        </div>
        <figcaption className="tnum mt-3 text-sm text-muted">
          {t(
            `Gini difference against the baseline, paired bootstrap on the same ${fmtInt(rows[0].n)} test loans.`,
            `Разница Gini с базовой моделью, парный бутстреп на одних и тех же ${fmtInt(rows[0].n)} тестовых кредитах.`,
          )}{" "}
          {rows
            .map((r) =>
              t(
                `${r.name}: ${fmtSigned(r.d.ci_low, 4)} to ${fmtSigned(r.d.ci_high, 4)}`,
                `${r.name}: от ${fmtSigned(r.d.ci_low, 4)} до ${fmtSigned(r.d.ci_high, 4)}`,
              ),
            )
            .join(". ")}
          .
        </figcaption>
      </figure>
    </div>
  );
}

export function Results() {
  const { t } = useLang();
  return (
    <section id="results" className="relative z-10 bg-ink/65 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            {t("The result, with its uncertainty", "Результат вместе с его неопределённостью")}
          </h2>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-muted">
            {t(
              `Gini on ${fmtInt(study.totals.test_loans)} test loans the models never saw, issued after every training loan. Each line is a 95% bootstrap interval from ${fmtInt(study.totals.n_bootstrap)} resamples.`,
              `Gini на ${fmtInt(study.totals.test_loans)} тестовых кредитах, которых модели не видели: все они выданы позже любого обучающего. Каждая линия — 95%-ный бутстреп-интервал по ${fmtInt(study.totals.n_bootstrap)} выборкам.`,
            )}
          </p>
        </Reveal>

        <div className="mt-12">
          <div className="tnum relative mb-1 h-5 text-xs text-muted md:mb-0 md:ml-[20.5rem] md:mr-[14.5rem]" aria-hidden="true">
            {TICKS.map((t, i) => (
              // End labels are anchored to the column edges so they never hang outside it.
              <span
                key={t}
                className={`absolute ${
                  i === 0 ? "" : i === TICKS.length - 1 ? "-translate-x-full" : "-translate-x-1/2"
                }`}
                style={{ left: pos(t) }}
              >
                {t.toFixed(1)}
              </span>
            ))}
          </div>
          <ul className="divide-y divide-line border-y border-line">
            {study.experiments.map((e, i) => (
              <IntervalRow key={e.id} e={e} index={i} />
            ))}
          </ul>
          <p className="mt-4 text-sm text-muted">
            {study.experiments.some((e) => !e.gini)
              ? t(
                  `E2 and E3 need a language model to read all ${fmtInt(study.totals.unique_texts)} unique descriptions. That run is under way, and no numbers are shown until it finishes. `,
                  `Для E2 и E3 языковая модель должна прочитать все ${fmtInt(study.totals.unique_texts)} уникальных описаний. Этот прогон ещё идёт, и до его конца числа не показываются. `,
                )
              : ""}
            {t("Source:", "Источник:")} <span className="font-mono text-[12.5px]">reports/runs/*/metrics.json</span>
          </p>
        </div>

        <Difference />
      </div>
    </section>
  );
}
