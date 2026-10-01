import { useCalm } from "../lib/useCalm";
import { motion, type MotionValue, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

// The question, in plain words. Each word lights as the reader reaches it, so the pace of
// the argument is the pace of the scroll.
const TEXT =
  "A credit model reads numbers: income, score, rate. For seven years, borrowers on Lending Club also wrote a few sentences to the strangers who would fund them. Then the field was removed. This study asks one question. Does that text say anything about default that the numbers do not already know?";

function Word({ word, range, progress }: { word: string; range: [number, number]; progress: MotionValue<number> }) {
  const opacity = useTransform(progress, range, [0.16, 1]);
  return (
    <motion.span style={{ opacity }} className="inline-block">
      {word}
    </motion.span>
  );
}

export function Hook() {
  const ref = useRef<HTMLParagraphElement>(null);
  const reduce = useCalm();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.82", "end 0.45"] });
  const words = TEXT.split(" ");

  return (
    <section id="question" className="relative z-10 bg-ink/70 py-28 md:py-44">
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <h2 className="sr-only">The question</h2>
        <p
          ref={ref}
          className="max-w-[26ch] font-display text-[clamp(1.9rem,4.4vw,4rem)] font-medium leading-[1.12] tracking-[-0.02em] md:max-w-[24ch] lg:ml-[12%]"
        >
          {reduce
            ? TEXT
            : words.map((w, i) => {
                const start = i / words.length;
                const end = Math.min(1, start + 2.5 / words.length);
                return (
                  <span key={i}>
                    <Word word={w} range={[start, end]} progress={scrollYProgress} />{" "}
                  </span>
                );
              })}
        </p>
      </div>
    </section>
  );
}
