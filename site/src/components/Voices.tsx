import { useCalm } from "../lib/useCalm";
import { ArrowLeft, ArrowRight, CheckCircle, Question, XCircle } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { useRef } from "react";
import { fmtInt, study, type Listing } from "../data/study";
import { EASE_OUT } from "../lib/motion";
import { HeatText } from "./HeatText";
import { Reveal } from "./Reveal";

const VERDICT = {
  right: { label: "Read correctly", Icon: CheckCircle, tone: "text-paper" },
  wrong: { label: "Misread", Icon: XCircle, tone: "text-paper" },
  debatable: { label: "Debatable", Icon: Question, tone: "text-muted" },
} as const;

/** The LLM's answer, printed as the JSON it actually returned. */
function LlmJson({ llm }: { llm: Listing["llm"] }) {
  const entries = Object.entries(llm);
  return (
    <pre className="overflow-x-auto font-mono text-[12.5px] leading-[1.7] text-muted">
      <code>
        {"{\n"}
        {entries.map(([k, v], i) => (
          <span key={k}>
            {"  "}
            <span className="text-faint">"{k}"</span>:{" "}
            <span className="text-paper">{typeof v === "string" ? `"${v}"` : String(v)}</span>
            {i < entries.length - 1 ? "," : ""}
            {"\n"}
          </span>
        ))}
        {"}"}
      </code>
    </pre>
  );
}

function ListingCard({ listing, index }: { listing: Listing; index: number }) {
  const reduce = useCalm();
  const v = listing.review ? VERDICT[listing.review.verdict] : null;
  const text = listing.desc.length > 430 ? `${listing.desc.slice(0, 430).trimEnd()}...` : listing.desc;

  return (
    <motion.li
      className="glass flex w-[min(86vw,30rem)] shrink-0 snap-start flex-col p-6 md:p-7"
      initial={reduce ? false : { opacity: 0, x: 48 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.7, delay: Math.min(index, 3) * 0.07, ease: EASE_OUT }}
    >
      <p className="flex items-center justify-between text-sm text-muted">
        <span className="tnum">
          {listing.year}, grade {listing.grade}
        </span>
        <span className={listing.defaulted ? "text-warm" : "text-muted"}>
          {listing.defaulted ? "Charged off" : "Repaid"}
        </span>
      </p>

      <p className="mt-5 text-[1.05rem] leading-[1.6]">
        <HeatText text={text} />
      </p>

      <div className="mt-6 border-t border-line pt-5">
        <LlmJson llm={listing.llm} />
      </div>

      {v && listing.review && (
        <p className="mt-5 flex gap-2.5 text-sm leading-relaxed text-paper/85">
          <v.Icon size={20} weight="fill" className={`mt-0.5 shrink-0 ${v.tone}`} aria-hidden="true" />
          <span>
            <span className="font-medium text-paper">{v.label}.</span> {listing.review.note}
          </span>
        </p>
      )}
    </motion.li>
  );
}

export function Voices() {
  const scroller = useRef<HTMLUListElement>(null);
  const reviewed = study.listings.filter((l) => l.review);
  const order = ["200256", "2086642", "1020958", "642370", "1583722", "3526633", "8394629", "5365409", "709197"];
  const cards = order
    .map((id) => reviewed.find((l) => l.id === id))
    .filter((l): l is Listing => Boolean(l));
  const wrong = reviewed.filter((l) => l.review?.verdict === "wrong").length;
  const { cost } = study.pilot;

  const nudge = (dir: 1 | -1) => {
    const el = scroller.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.min(520, el.clientWidth * 0.85), behavior: "smooth" });
  };

  return (
    <section id="voices" className="relative z-10 py-24 md:py-36">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[20ch] font-display text-[clamp(2rem,4.2vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.025em]">
            What a 7B model reads in a loan request
          </h2>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-muted">
            Each description was sent to {study.pilot.model.split("/")[1]} with a fixed schema. In a{" "}
            {cost.n}-loan pilot it returned valid JSON {Math.round(cost.valid_rate * cost.n)} times
            out of {cost.n}. Valid is not the same as right: a manual check found {wrong} clear
            misreads.
            {study.llm_run
              ? ` The full run then covered all ${fmtInt(study.llm_run.n)} loans, and ${study.llm_run.n_null} answers failed the schema twice and were left empty.`
              : ""}
          </p>
        </Reveal>
      </div>

      <ul
        ref={scroller}
        className="rail mt-12 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        tabIndex={0}
        aria-label="Reviewed pilot descriptions"
      >
        {cards.map((l, i) => (
          <ListingCard key={l.id} listing={l} index={i} />
        ))}
      </ul>

      <div className="mx-auto mt-4 flex max-w-[1400px] items-center justify-between gap-6 px-5 md:px-10">
        <p className="text-sm text-muted">
          Real descriptions and real model output. Word colours are the text-only model's weights. Filler words are left plain.
        </p>
        <div className="flex shrink-0 gap-2">
          <button type="button" className="btn btn-ghost !h-12 !w-12 justify-center !px-0" onClick={() => nudge(-1)} aria-label="Previous descriptions">
            <ArrowLeft size={18} aria-hidden="true" />
          </button>
          <button type="button" className="btn btn-ghost !h-12 !w-12 justify-center !px-0" onClick={() => nudge(1)} aria-label="Next descriptions">
            <ArrowRight size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  );
}
