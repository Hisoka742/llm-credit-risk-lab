import { study } from "../data/study";
import { Reveal } from "./Reveal";

// The project was built with an AI coding agent. What matters to a reviewer is what the
// process caught, so this section lists real failures and what now prevents them.
const CATCHES = [
  {
    title: "A cleaning rule that would have deleted borrower text",
    body: "The first HTML stripper treated every angle bracket as a tag. Real descriptions say things like a balance going from < 40% to > 80% of the limit. Sampling the raw text exposed it before any model ran.",
  },
  {
    title: "A crashed model server that looked like progress",
    body: "When the GPU server died, the extractor kept counting failed requests as done. It now stops after 50 straight failures and refuses to write a feature file that contains them.",
  },
  {
    title: "A package that silently dropped a module",
    body: "An exclude rule for the data folder also removed the data-loading code from the upload. A test now fails if that module is missing from the package.",
  },
  {
    title: "Saved answers the resume step could not find",
    body: "The extraction ran over several GPU sessions. The hosting service packed the saved answers into one archive, and the resume step only looked for folders, so it reported zero. It now searches archives too and merges every copy it finds.",
  },
];

export function Build() {
  return (
    <section id="build" className="relative z-10 bg-ink/55 py-24 md:py-36">
      <div className="mx-auto grid max-w-[1400px] gap-12 px-5 md:px-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-24">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <Reveal>
            <h2 className="max-w-[14ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
              Built with an AI agent, checked by tests
            </h2>
            <p className="mt-6 max-w-[40ch] text-lg leading-relaxed text-muted">
              The code was written with an AI coding agent and reviewed step by step. These are
              four things that went wrong on the way, and what guards against each now.
              {study.totals.tests ? ` The suite has ${study.totals.tests} tests.` : ""}
            </p>
          </Reveal>
        </div>

        <ol className="space-y-12">
          {CATCHES.map((c, i) => (
            <li key={c.title}>
              <Reveal delay={i * 0.04}>
                <h3 className="font-display text-2xl font-medium leading-tight tracking-[-0.015em]">{c.title}</h3>
                <p className="mt-3 max-w-[58ch] leading-relaxed text-muted">{c.body}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
