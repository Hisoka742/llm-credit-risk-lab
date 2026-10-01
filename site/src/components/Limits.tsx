import { useLang } from "../lib/i18n";
import { Reveal } from "./Reveal";

// Limitations are content, stated as plainly as the results.
const LIMITS = [
  {
    en: ["The text ends in March 2014.", "Lending Club removed the description field, so the out-of-time test window is four issue months. Stability over time rests on two quarters."],
    ru: ["Тексты заканчиваются в марте 2014 года.", "Lending Club убрал поле с описанием, поэтому тестовое окно «вне времени обучения» — всего четыре месяца выдачи. Вывод о стабильности во времени опирается на два квартала."],
  },
  {
    en: ["Writers are a selected group.", "Borrowers who wrote a description are not a random sample of applicants. Nothing here transfers to loans without free text."],
    ru: ["Те, кто писал, — не случайная выборка.", "Заёмщики, оставившие описание, не представляют всех заявителей. На кредиты без свободного текста эти выводы не переносятся."],
  },
  {
    en: ["The baseline already contains a risk model.", "Interest rate and grade encode Lending Club's own assessment, made by people who saw the same text. A small gain on top of that is expected."],
    ru: ["В базовой модели уже есть чужая оценка риска.", "Ставка и грейд отражают собственную оценку Lending Club, которую ставили люди, видевшие тот же текст. Небольшой прирост поверх неё ожидаем."],
  },
  {
    en: ["Accepted loans only.", "There is no reject inference. Every model is trained and tested on loans that were approved."],
    ru: ["Только одобренные кредиты.", "Анализа отказов нет. Все модели обучены и проверены на кредитах, которые были выданы."],
  },
  {
    en: ["One seed per experiment.", "The intervals cover test sampling, not training randomness. A difference of a few thousandths of Gini is comparable to seed noise."],
    ru: ["Один seed на эксперимент.", "Интервалы учитывают случайность тестовой выборки, но не случайность обучения. Разница в несколько тысячных Gini сравнима с шумом от смены seed."],
  },
  {
    en: ["The language model misreads.", "In a hand-checked pilot, valid JSON still carried wrong labels, and no larger audit was done. The result describes these noisy labels, not what a careful human reader would extract."],
    ru: ["Языковая модель ошибается при чтении.", "В пилоте, проверенном вручную, корректный JSON всё равно содержал неверные метки, а более крупной проверки не было. Результат описывает эти шумные метки, а не то, что извлёк бы внимательный человек."],
  },
];

export function Limits() {
  const { t, lang } = useLang();
  return (
    <section id="limits" className="relative z-10 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[16ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            {t("What this study cannot claim", "Чего это исследование утверждать не может")}
          </h2>
        </Reveal>
        <ul className="mt-14 grid gap-x-16 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
          {LIMITS.map((l, i) => (
            <li key={l.en[0]}>
              <Reveal delay={(i % 3) * 0.06}>
                <h3 className="font-display text-xl font-medium leading-snug tracking-[-0.01em]">{l[lang][0]}</h3>
                <p className="mt-3 max-w-[44ch] leading-relaxed text-muted">{l[lang][1]}</p>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
