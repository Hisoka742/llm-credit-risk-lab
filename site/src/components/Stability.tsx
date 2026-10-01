import { experiment, fmt, fmtInt, fmtPct, study } from "../data/study";
import { useLang } from "../lib/i18n";
import { Reveal } from "./Reveal";

const SIZE = 320;
const PAD = 34;
const MAX = 0.4;
const sx = (v: number) => PAD + (v / MAX) * (SIZE - PAD - 22);
const sy = (v: number) => SIZE - PAD - (v / MAX) * (SIZE - PAD - 12);

/** Reliability curve drawn from the exported decile table: predicted vs observed default. */
function Reliability() {
  const e0 = experiment("e0")?.calibration ?? [];
  const e1 = experiment("e1")?.calibration ?? [];
  const path = (rows: typeof e0) =>
    rows.map((r, i) => `${i ? "L" : "M"}${sx(r.mean_pred).toFixed(1)},${sy(r.observed).toFixed(1)}`).join(" ");
  const ticks = [0, 0.1, 0.2, 0.3, 0.4];
  const { t } = useLang();

  return (
    <figure>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="w-full max-w-[26rem]"
        role="img"
        aria-label={t(
          "Reliability curve: predicted default probability against observed default rate, by score decile, for the baseline and the embedding model. Both follow the diagonal.",
          "Кривая надёжности: предсказанная вероятность дефолта против наблюдаемой доли дефолтов по децилям скора, для базовой модели и модели с эмбеддингами. Обе идут вдоль диагонали.",
        )}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line x1={sx(t)} y1={sy(0)} x2={sx(t)} y2={sy(MAX)} stroke="rgb(241 236 226 / 0.08)" />
            <line x1={sx(0)} y1={sy(t)} x2={sx(MAX)} y2={sy(t)} stroke="rgb(241 236 226 / 0.08)" />
            <text x={sx(t)} y={SIZE - 12} textAnchor="middle" fontSize="10" fill="#a8a399">
              {Math.round(t * 100)}%
            </text>
            <text x={PAD - 8} y={sy(t) + 3} textAnchor="end" fontSize="10" fill="#a8a399">
              {Math.round(t * 100)}%
            </text>
          </g>
        ))}
        <line x1={sx(0)} y1={sy(0)} x2={sx(MAX)} y2={sy(MAX)} stroke="#8f8b84" strokeDasharray="4 4" />
        <path d={path(e0)} fill="none" stroke="rgb(241 236 226 / 0.45)" strokeWidth="2" />
        <path d={path(e1)} fill="none" stroke="#f1ece2" strokeWidth="2" />
        {e1.map((r) => (
          <circle key={r.mean_pred} cx={sx(r.mean_pred)} cy={sy(r.observed)} r="3.5" fill="#f1ece2" stroke="#0b0e13" strokeWidth="1.5" />
        ))}
      </svg>
      <figcaption className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted">
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-5 bg-paper" aria-hidden="true" /> {t("E1, with embeddings", "E1, с эмбеддингами")}
        </span>
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-5 bg-paper/45" aria-hidden="true" /> {t("E0, baseline", "E0, базовая модель")}
        </span>
        <span>{t("Predicted (x) against observed (y), by score decile.", "Предсказание (x) против факта (y), по децилям скора.")}</span>
      </figcaption>
    </figure>
  );
}

export function Stability() {
  const e0 = experiment("e0");
  const e1 = experiment("e1");
  const cost = study.embedding_cost;
  const pilot = study.pilot.cost;
  const run = study.llm_run;
  const { t, ru } = useLang();

  return (
    <section id="stability" className="relative z-10 bg-ink/60 py-24 md:py-36">
      <div className="mx-auto grid max-w-[1400px] gap-14 px-5 md:px-10 lg:grid-cols-[1fr_1.15fr] lg:gap-20">
        <Reveal>
          <Reliability />
        </Reveal>

        <div>
          <Reveal>
            <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
              {t("Calibrated, stable, and cheap to run", "Калибровка, стабильность и цена запуска")}
            </h2>
          </Reveal>

          <dl className="mt-10 space-y-8">
            {e0?.mean_pd !== undefined && e0.observed !== undefined && (
              <Reveal>
                <dt className="font-display text-xl font-medium">
                  {t("Predicted risk matches reality", "Предсказанный риск совпадает с фактом")}
                </dt>
                <dd className="mt-2 max-w-[56ch] leading-relaxed text-muted">
                  {ru ? (
                    <>
                      Базовая модель предсказывает на тесте среднюю вероятность дефолта{" "}
                      <span className="tnum text-paper">{fmtPct(e0.mean_pd)}</span>. Фактическая доля —{" "}
                      <span className="tnum text-paper">{fmtPct(e0.observed)}</span>. Веса классов не
                      использовались, поэтому вероятности остаются честными.
                    </>
                  ) : (
                    <>
                      The baseline predicts an average default probability of{" "}
                      <span className="tnum text-paper">{fmtPct(e0.mean_pd)}</span> on the test set. The
                      observed rate is <span className="tnum text-paper">{fmtPct(e0.observed)}</span>. No
                      class weights were used, so the probabilities stay honest.
                    </>
                  )}
                </dd>
              </Reveal>
            )}
            {e0?.psi_train_test !== undefined && e1?.psi_train_test !== undefined && (
              <Reveal>
                <dt className="font-display text-xl font-medium">
                  {t("The score distribution does not drift", "Распределение скора не дрейфует")}
                </dt>
                <dd className="mt-2 max-w-[56ch] leading-relaxed text-muted">
                  {t(
                    "Population stability index between train and test scores:",
                    "Индекс стабильности популяции (PSI) между скорами на обучении и на тесте:",
                  )}{" "}
                  <span className="tnum text-paper">{fmt(e0.psi_train_test, 4)}</span>{" "}
                  {t("for the baseline and", "у базовой модели и")}{" "}
                  <span className="tnum text-paper">{fmt(e1.psi_train_test, 4)}</span>{" "}
                  {t("with embeddings. Below 0.10 counts as stable.", "с эмбеддингами. Ниже 0.10 считается стабильным.")}
                </dd>
              </Reveal>
            )}
            {cost && (
              <Reveal>
                <dt className="font-display text-xl font-medium">
                  {t("What reading the text costs", "Сколько стоит прочитать текст")}
                </dt>
                <dd className="mt-2 max-w-[56ch] leading-relaxed text-muted">
                  {t("Embedding one description takes", "Эмбеддинг одного описания занимает")}{" "}
                  <span className="tnum text-paper">
                    {cost.ms_per_application.toFixed(1)} {t("ms", "мс")}
                  </span>{" "}
                  {t(
                    `on a laptop CPU, about ${Math.round(cost.mean_tokens)} tokens. The language model needs`,
                    `на процессоре ноутбука, около ${Math.round(cost.mean_tokens)} токенов. Языковой модели нужно`,
                  )}{" "}
                  <span className="tnum text-paper">{Math.round((run ?? pilot).mean_prompt_tokens)}</span>{" "}
                  {t("tokens in and", "токена на входе и")}{" "}
                  <span className="tnum text-paper">{Math.round((run ?? pilot).mean_completion_tokens)}</span>{" "}
                  {t("out, roughly", "на выходе, примерно")}{" "}
                  <span className="tnum text-paper">
                    {(run?.gpu_seconds_per_application ?? pilot.accelerator_seconds_per_application).toFixed(2)}{" "}
                    {t("GPU-seconds", "GPU-секунды")}
                  </span>{" "}
                  {run
                    ? t(
                        `per loan on a free T4, timed over ${fmtInt(run.n_timed_calls)} calls.`,
                        `на кредит на бесплатной T4; замер по ${fmtInt(run.n_timed_calls)} вызовам.`,
                      )
                    : t(`per loan in a ${pilot.n}-loan pilot on a T4.`, `на кредит в пилоте из ${pilot.n} кредитов на T4.`)}
                </dd>
              </Reveal>
            )}
          </dl>
        </div>
      </div>
    </section>
  );
}
