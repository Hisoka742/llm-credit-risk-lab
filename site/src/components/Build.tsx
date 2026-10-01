import { study } from "../data/study";
import { useLang } from "../lib/i18n";
import { Reveal } from "./Reveal";

// The project was built with an AI coding agent. What matters to a reviewer is what the
// process caught, so this section lists real failures and what now prevents them.
const CATCHES = [
  {
    en: ["A cleaning rule that would have deleted borrower text", "The first HTML stripper treated every angle bracket as a tag. Real descriptions say things like a balance going from < 40% to > 80% of the limit. Sampling the raw text exposed it before any model ran."],
    ru: ["Правило очистки, которое удалило бы слова заёмщиков", "Первая версия очистки HTML считала тегом любую угловую скобку. В реальных описаниях пишут, например, что баланс вырос с < 40% до > 80% лимита. Ошибку показал просмотр сырого текста — до запуска первой модели."],
  },
  {
    en: ["A crashed model server that looked like progress", "When the GPU server died, the extractor kept counting failed requests as done. It now stops after 50 straight failures and refuses to write a feature file that contains them."],
    ru: ["Упавший сервер модели, похожий на прогресс", "Когда сервер на GPU падал, программа продолжала считать неудачные запросы выполненными. Теперь она останавливается после 50 сбоев подряд и не записывает файл признаков, в котором они есть."],
  },
  {
    en: ["A package that silently dropped a module", "An exclude rule for the data folder also removed the data-loading code from the upload. A test now fails if that module is missing from the package."],
    ru: ["Архив, из которого молча пропал модуль", "Правило исключения папки с данными заодно убрало из загружаемого архива код загрузки данных. Теперь тест падает, если этого модуля в архиве нет."],
  },
  {
    en: ["Saved answers the resume step could not find", "The extraction ran over several GPU sessions. The hosting service packed the saved answers into one archive, and the resume step only looked for folders, so it reported zero. It now searches archives too and merges every copy it finds."],
    ru: ["Сохранённые ответы, которые не нашёл шаг возобновления", "Извлечение шло несколько сессий на GPU. Сервис упаковал сохранённые ответы в один архив, а шаг возобновления искал только папки и сообщил о нуле. Теперь он просматривает и архивы и объединяет все найденные копии."],
  },
];

export function Build() {
  const { t, lang } = useLang();
  return (
    <section id="build" className="relative z-10 bg-ink/55 py-24 md:py-36">
      <div className="mx-auto grid max-w-[1400px] gap-12 px-5 md:px-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-24">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <Reveal>
            <h2 className="max-w-[14ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
              {t("Built with an AI agent, checked by tests", "Сделано с ИИ-агентом, проверено тестами")}
            </h2>
            <p className="mt-6 max-w-[40ch] text-lg leading-relaxed text-muted">
              {t(
                "The code was written with an AI coding agent and reviewed step by step. These are four things that went wrong on the way, and what guards against each now.",
                "Код написан вместе с ИИ-агентом и проверялся шаг за шагом. Вот четыре вещи, которые пошли не так, и что теперь защищает от каждой.",
              )}
              {study.totals.tests
                ? t(` The suite has ${study.totals.tests} tests.`, ` В наборе ${study.totals.tests} автотестов.`)
                : ""}
            </p>
          </Reveal>
        </div>

        <ol className="space-y-12">
          {CATCHES.map((c, i) => (
            <li key={c.en[0]}>
              <Reveal delay={i * 0.04}>
                <h3 className="font-display text-2xl font-medium leading-tight tracking-[-0.015em]">{c[lang][0]}</h3>
                <p className="mt-3 max-w-[58ch] leading-relaxed text-muted">{c[lang][1]}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
