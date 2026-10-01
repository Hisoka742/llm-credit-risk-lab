import { Reveal } from "./Reveal";

// Limitations are content, stated as plainly as the results.
const LIMITS = [
  {
    lead: "The text ends in March 2014.",
    body: "Lending Club removed the description field, so the out-of-time test window is four issue months. Stability over time rests on two quarters.",
  },
  {
    lead: "Writers are a selected group.",
    body: "Borrowers who wrote a description are not a random sample of applicants. Nothing here transfers to loans without free text.",
  },
  {
    lead: "The baseline already contains a risk model.",
    body: "Interest rate and grade encode Lending Club's own assessment, made by people who saw the same text. A small gain on top of that is expected.",
  },
  {
    lead: "Accepted loans only.",
    body: "There is no reject inference. Every model is trained and tested on loans that were approved.",
  },
  {
    lead: "One seed per experiment.",
    body: "The intervals cover test sampling, not training randomness. A difference of a few thousandths of Gini is comparable to seed noise.",
  },
  {
    lead: "The language model misreads.",
    body: "In a hand-checked pilot, valid JSON still carried wrong labels, and no larger audit was done. The result describes these noisy labels, not what a careful human reader would extract.",
  },
];

export function Limits() {
  return (
    <section id="limits" className="relative z-10 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[16ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            What this study cannot claim
          </h2>
        </Reveal>
        <ul className="mt-14 grid gap-x-16 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
          {LIMITS.map((l, i) => (
            <li key={l.lead}>
              <Reveal delay={(i % 3) * 0.06}>
                <h3 className="font-display text-xl font-medium leading-snug tracking-[-0.01em]">{l.lead}</h3>
                <p className="mt-3 max-w-[44ch] leading-relaxed text-muted">{l.body}</p>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
