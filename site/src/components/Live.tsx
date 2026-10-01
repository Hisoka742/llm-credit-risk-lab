import { ArrowCounterClockwise, CircleNotch } from "@phosphor-icons/react";
import { type FormEvent, useEffect, useId, useState } from "react";
import { fmtInt, fmtPct, type LiveProfile, type LiveRun, study } from "../data/study";
import { useLang } from "../lib/i18n";
import { Reveal } from "./Reveal";

// Two modes, same panel:
// - live: the API from `python -m scripts.serve` is reachable, so any text can be sent. In
//   development the Vite server proxies /api to it; a production build needs VITE_API_URL.
// - recorded: no API. The page shows real runs saved by `python -m scripts.record_live`
//   (study.live), clearly labelled as recorded, so the static site still shows the reader at work.
const API: string = import.meta.env.VITE_API_URL ?? "";
const TRY_API = import.meta.env.DEV || Boolean(API);
const recorded = study.live;

type Health = { reader: string; trained_on: string; max_text_chars: number };
type Analysis = LiveRun & { profile_id: string; reader: string; cached: boolean };

const FIELDS: [string, string, string][] = [
  ["loan_purpose_category", "Purpose", "Цель кредита"],
  ["financial_stress", "Financial stress (0 to 3)", "Финансовый стресс (0–3)"],
  ["employment_stability", "Employment stability (0 to 3)", "Стабильность занятости (0–3)"],
  ["mentions_other_debts", "Mentions other debts", "Упоминает другие долги"],
  ["mentions_job_loss_or_income_drop", "Mentions job loss or income drop", "Упоминает потерю работы или дохода"],
  ["mentions_medical_or_family_emergency", "Mentions medical or family emergency", "Упоминает болезнь или семейные обстоятельства"],
  ["has_repayment_plan", "Has a repayment plan", "Есть план погашения"],
  ["text_quality", "Text quality (0 to 3)", "Качество текста (0–3)"],
];

const TEXT_LABEL: Record<string, [string, string]> = {
  hardship: ["Job loss and surgery", "Потеря работы и операция"],
  stable_plan: ["Stable job, clear plan", "Стабильная работа и план"],
  two_words: ["Two words", "Два слова"],
  business: ["Opening a bakery", "Открытие пекарни"],
  stable_plan_ru: ["Written in Russian", "Текст на русском"],
};

const shortName = (model: string) => model.split("/").pop() ?? model;

function PdFigure({ label, value, strong }: { label: string; value: number | null; strong?: boolean }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`tnum mt-1 font-display text-2xl font-medium tracking-[-0.02em] sm:text-3xl ${strong ? "text-paper" : "text-paper/70"}`}>
        {value === null ? <span className="text-faint">...</span> : fmtPct(value)}
      </dd>
    </div>
  );
}

export function Live() {
  const { t, ru } = useLang();
  const [health, setHealth] = useState<Health | null>(null);
  const [apiProfiles, setApiProfiles] = useState<LiveProfile[]>([]);
  const [selected, setSelected] = useState<string>(recorded?.profiles[0]?.id ?? "");
  // In recorded mode a prepared text is always selected. In live mode it is only a shortcut.
  const [textKey, setTextKey] = useState<string>("hardship");
  const [text, setText] = useState<string>(recorded?.texts.find((x) => x.id === "hardship")?.text ?? "");
  const [result, setResult] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textId = useId();

  useEffect(() => {
    if (!TRY_API) return;
    const ctl = new AbortController();
    const get = (path: string) =>
      fetch(`${API}${path}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject()));
    Promise.all([get("/api/health"), get("/api/profiles")])
      .then(([h, p]: [Health, LiveProfile[]]) => {
        if (!p.length) return;
        setHealth(h);
        setApiProfiles(p);
        setSelected((cur) => (p.some((x) => x.id === cur) ? cur : p[0].id));
      })
      .catch(() => undefined); // API not running: fall back to the recorded runs
    return () => ctl.abort();
  }, []);

  const live = Boolean(health);
  const profiles = live ? apiProfiles : (recorded?.profiles ?? []);
  const profile = profiles.find((p) => p.id === selected) ?? profiles[0];
  if (!profile) return null;

  const reader = shortName(health?.reader ?? recorded?.reader ?? "");
  const trainedOn = shortName(health?.trained_on ?? recorded?.trained_on ?? "");
  const maxChars = health?.max_text_chars ?? recorded?.max_text_chars ?? 1500;
  const prepared = recorded?.texts ?? [];

  const choose = (key: string, value: string) => {
    setTextKey(key);
    setText(value);
    setResult(null);
    setError(null);
  };
  const pick = (p: LiveProfile) => {
    setSelected(p.id);
    setResult(null);
    setError(null);
    if (textKey === "original") setText(p.desc);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!live || busy || !text.trim()) return;
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
        throw new Error(typeof body.detail === "string" ? body.detail : t("The request was rejected.", "Запрос отклонён."));
      }
      setResult(body as Analysis);
    } catch (err) {
      setResult(null);
      setError(
        err instanceof TypeError
          ? t("The demo server is not reachable.", "Демо-сервер недоступен.")
          : (err as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  // The run shown in the panel: the live answer for this profile, or the recorded one.
  const run: LiveRun | null = live
    ? result && result.profile_id === profile.id
      ? result
      : null
    : (recorded?.runs.find((x) => x.profile_id === profile.id && x.text_id === textKey) ?? null);
  const delta = run ? run.pd_your_text - profile.pd_original_text : null;
  const tooLong = text.length > maxChars;
  const third = live ? t("Your text", "Ваш текст") : t("This text", "Этот текст");

  const show = (v: string | number | boolean | null | undefined): string =>
    v === null || v === undefined
      ? t("none", "нет")
      : typeof v === "boolean"
        ? v ? t("yes", "да") : t("no", "нет")
        : String(v).replace(/_/g, " ");

  const chip = (active: boolean) =>
    `rounded-full border px-3.5 py-2 text-sm transition-colors duration-150 ${
      active ? "border-paper bg-paper text-ink" : "border-line text-muted hover:border-paper/50 hover:text-paper"
    }`;

  return (
    <section id="live" className="relative z-10 bg-ink/65 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[18ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            {live
              ? t("Same borrower, your words", "Тот же заёмщик, ваши слова")
              : t("Same borrower, different words", "Тот же заёмщик, другие слова")}
          </h2>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-muted">
            {live
              ? t(
                  `Pick a real loan from the test set and rewrite its description. ${reader} reads your text now, and the trained model scores the same borrower again. Income, rate, credit history and every other number stay fixed.`,
                  `Выберите настоящий кредит из тестовой выборки и перепишите его описание. ${reader} прочитает ваш текст прямо сейчас, а обученная модель заново оценит того же заёмщика. Доход, ставка, кредитная история и все остальные числа не меняются.`,
                )
              : t(
                  `Pick a real loan from the test set and swap its description for another text. ${reader} read each text, and the trained model scored the same borrower again. Income, rate, credit history and every other number stay fixed.`,
                  `Выберите настоящий кредит из тестовой выборки и замените его описание другим текстом. ${reader} прочитал каждый текст, а обученная модель заново оценила того же заёмщика. Доход, ставка, кредитная история и все остальные числа не меняются.`,
                )}
          </p>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
          <form onSubmit={submit} className="min-w-0">
            <fieldset>
              <legend className="text-sm text-muted">{t("Borrower", "Заёмщик")}</legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {profiles.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => pick(p)}
                    aria-pressed={p.id === profile.id}
                    className={`tnum ${chip(p.id === profile.id)}`}
                  >
                    {t(`Grade ${p.grade}, $${fmtInt(p.loan_amnt / 1000)}k`, `Грейд ${p.grade}, $${fmtInt(p.loan_amnt / 1000)} тыс.`)}
                  </button>
                ))}
              </div>
            </fieldset>

            <p className="tnum mt-5 text-sm leading-relaxed text-muted">
              {t(
                `Issued ${profile.issued}. $${fmtInt(profile.loan_amnt)} at ${profile.int_rate.toFixed(2)}%, income $${fmtInt(profile.annual_inc)}, stated purpose ${profile.purpose.replace(/_/g, " ")}. This loan was`,
                `Выдан ${profile.issued}. $${fmtInt(profile.loan_amnt)} под ${profile.int_rate.toFixed(2)}%, доход $${fmtInt(profile.annual_inc)}, заявленная цель: ${profile.purpose.replace(/_/g, " ")}. Этот кредит`,
              )}{" "}
              <span className={profile.defaulted ? "text-warm" : "text-paper"}>
                {profile.defaulted ? t("charged off", "списан как безнадёжный") : t("repaid", "погашен")}
              </span>
              .
            </p>

            <fieldset className="mt-7">
              <legend className="text-sm text-muted">
                {live ? t("Start from a prepared text", "Начать с готового текста") : t("Description", "Описание")}
              </legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {prepared.map((x) => (
                  <button
                    key={x.id}
                    type="button"
                    onClick={() => choose(x.id, x.text)}
                    aria-pressed={textKey === x.id && text === x.text}
                    className={chip(textKey === x.id && text === x.text)}
                  >
                    {(TEXT_LABEL[x.id] ?? [x.id, x.id])[ru ? 1 : 0]}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => choose("original", profile.desc)}
                  aria-pressed={textKey === "original" && text === profile.desc}
                  className={chip(textKey === "original" && text === profile.desc)}
                >
                  <ArrowCounterClockwise size={15} className="mr-1.5 inline -translate-y-px" aria-hidden="true" />
                  {t("Original text", "Исходный текст")}
                </button>
              </div>
            </fieldset>

            <label htmlFor={textId} className="sr-only">
              {t("Description text", "Текст описания")}
            </label>
            <textarea
              id={textId}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setTextKey("custom");
              }}
              readOnly={!live}
              rows={7}
              className={`mt-4 w-full resize-y rounded-2xl border border-line bg-ink-2/80 p-4 leading-relaxed placeholder:text-faint ${live ? "text-paper" : "text-paper/85"}`}
              placeholder={t("Write what this borrower might have said.", "Напишите, что мог бы сказать этот заёмщик.")}
            />

            {live ? (
              <>
                <p className={`tnum mt-1.5 text-xs ${tooLong ? "text-paper" : "text-faint"}`}>
                  {t(
                    `${fmtInt(text.length)} of ${fmtInt(maxChars)} characters`,
                    `${fmtInt(text.length)} из ${fmtInt(maxChars)} символов`,
                  )}
                  {tooLong ? t(". Shorten the text to send it.", ". Сократите текст, чтобы отправить.") : ""}
                </p>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button type="submit" className="btn btn-primary" disabled={busy || tooLong || !text.trim()} aria-busy={busy}>
                    {busy && <CircleNotch size={18} weight="bold" className="animate-spin" aria-hidden="true" />}
                    {busy ? t("Reading", "Читает") : t("Read it and score", "Прочитать и оценить")}
                  </button>
                </div>
                {error && (
                  <p role="alert" className="mt-4 max-w-[56ch] text-sm leading-relaxed text-paper">
                    {error}
                  </p>
                )}
              </>
            ) : (
              <p className="mt-3 max-w-[58ch] text-sm leading-relaxed text-muted">
                {t(
                  `These are real runs recorded on ${recorded?.recorded_on} with ${reader}. Typing your own text needs the demo server from the repository:`,
                  `Это настоящие запуски, записанные ${recorded?.recorded_on} с ${reader}. Чтобы ввести свой текст, нужен демо-сервер из репозитория:`,
                )}{" "}
                <span className="font-mono text-[12.5px] text-paper/85">python -m scripts.serve</span>
              </p>
            )}
          </form>

          <div className="glass min-w-0 p-6 md:p-8" aria-live="polite">
            <dl className="grid grid-cols-3 gap-3">
              <PdFigure label={t("No text", "Без текста")} value={profile.pd_no_text} />
              <PdFigure label={t("Original text", "Исходный текст")} value={profile.pd_original_text} />
              <PdFigure label={third} value={run ? run.pd_your_text : null} strong />
            </dl>
            <p className="tnum mt-4 min-h-[3rem] text-sm leading-relaxed text-muted">
              {delta === null
                ? t(
                    "Predicted probability of default. Send a description to fill the third figure.",
                    "Предсказанная вероятность дефолта. Отправьте описание, чтобы появилось третье число.",
                  )
                : Math.abs(delta) < 0.0005
                  ? t(
                      "This text leaves the predicted probability of default unchanged.",
                      "Этот текст не меняет предсказанную вероятность дефолта.",
                    )
                  : t(
                      `This text moves the predicted probability of default ${delta > 0 ? "up" : "down"} by ${(Math.abs(delta) * 100).toFixed(1)} points against the original text.`,
                      `Этот текст ${delta > 0 ? "повышает" : "снижает"} предсказанную вероятность дефолта на ${(Math.abs(delta) * 100).toFixed(1)} п. п. относительно исходного текста.`,
                    )}
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
                  <th scope="col" className="py-3 pr-3 font-normal">{t("Extracted field", "Извлечённое поле")}</th>
                  <th scope="col" className="py-3 pr-3 font-normal">{t("Original", "Исходный")}</th>
                  <th scope="col" className="py-3 pr-3 font-normal">{live ? t("Yours", "Ваш") : t("This text", "Этот")}</th>
                  <th scope="col" className="py-3 text-right font-normal">{t("Effect", "Эффект")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line border-y border-line">
                {FIELDS.map(([f, en, rus]) => {
                  const before = show(profile.original_reading[f]);
                  const after = run ? show(run.reading?.[f]) : "";
                  const c = run?.contributions.find((x) => x.field === f)?.log_odds;
                  return (
                    <tr key={f}>
                      <th scope="row" className="py-2.5 pr-3 text-left font-normal text-muted">{ru ? rus : en}</th>
                      <td className="tnum py-2.5 pr-3 text-paper/70">{before}</td>
                      <td className={`tnum py-2.5 pr-3 ${run && after !== before ? "font-medium text-paper" : "text-paper/70"}`}>
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

            {run && run.reading === null && (
              <p className="mt-4 text-sm leading-relaxed text-paper">
                {t(
                  "The model's answer did not match the schema twice, so the text features were scored as missing.",
                  "Ответ модели дважды не прошёл схему, поэтому текстовые признаки учтены как пропущенные.",
                )}
              </p>
            )}
            <p className="mt-5 text-sm leading-relaxed text-muted">
              {t(
                "The Original column is the reading the model was trained on. Effect is each field's push on the score in log-odds: positive raises the predicted risk.",
                "Колонка «Исходный» — чтение, на котором модель обучалась. Эффект — вклад поля в скор в логарифме шансов: положительный повышает предсказанный риск.",
              )}
              {run
                ? t(
                    ` Read by ${reader} in ${run.latency_s.toFixed(1)} s, ${run.prompt_tokens} tokens in and ${run.completion_tokens} out.`,
                    ` Прочитано ${reader} за ${run.latency_s.toFixed(1)} с: ${run.prompt_tokens} токенов на входе, ${run.completion_tokens} на выходе.`,
                  )
                : ""}
            </p>
            {reader !== trainedOn && (
              <p className="mt-3 text-sm leading-relaxed text-muted">
                {t(
                  `The scoring model learned from ${trainedOn}'s readings, and ${reader} is a different reader. Treat the change as an illustration of the mechanism, not as a validated prediction.`,
                  `Модель скоринга училась на чтениях ${trainedOn}, а ${reader} — другой читатель. Считайте изменение иллюстрацией механизма, а не проверенным прогнозом.`,
                )}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
