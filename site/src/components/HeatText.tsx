import { motion } from "motion/react";
import { type ReactNode, useMemo } from "react";
import { study } from "../data/study";
import { EASE_OUT, heatColor, tokenize } from "../lib/motion";
import { useCalm } from "../lib/useCalm";

type Props = {
  text: string;
  /** Animate each word in, then let the heat resolve: used once, in the hero. */
  resolve?: boolean;
  className?: string;
};

/**
 * Borrower text with each word tinted by its weight in the text-only model: warm words are
 * associated with default, cool words with repayment, untinted words carry almost no weight.
 * Colour is never the only carrier: the legend and the terms section state the same thing.
 */
export function HeatText({ text, resolve = false, className }: Props) {
  const reduce = useCalm();
  const tokens = useMemo(() => tokenize(text), [text]);

  // The last two words are rendered as one unbreakable unit, so a single word never sits
  // alone on the final line.
  const wordIndexes = tokens.flatMap((t, i) => (t.word ? [i] : []));
  const tailStart = wordIndexes.length >= 2 ? wordIndexes[wordIndexes.length - 2] : tokens.length;

  let wordIndex = 0;
  const renderToken = (i: number): ReactNode => {
    const t = tokens[i];
    if (!t.word) return <span key={i}>{t.text}</span>;
    const color = heatColor(study.word_weights[t.text.toLowerCase()]);
    if (!resolve || reduce) {
      return (
        <span key={i} style={color ? { color } : undefined}>
          {t.text}
        </span>
      );
    }
    const delay = 0.25 + wordIndex++ * 0.055;
    return (
      <motion.span
        key={i}
        className="inline-block"
        initial={{ opacity: 0, y: "0.35em", filter: "blur(8px)", color: "#f1ece2" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)", color: color ?? "#f1ece2" }}
        transition={{
          duration: 0.8,
          delay,
          ease: EASE_OUT,
          // The word arrives first, then the model's reading settles onto it.
          color: { duration: 0.9, delay: delay + 0.55, ease: "easeOut" },
        }}
      >
        {t.text}
      </motion.span>
    );
  };

  const head = tokens.slice(0, tailStart).map((_, i) => renderToken(i));
  const tail = tokens.slice(tailStart).map((_, k) => renderToken(tailStart + k));

  return (
    <span className={className}>
      {head}
      {tail.length > 0 && <span className="inline-block whitespace-nowrap">{tail}</span>}
    </span>
  );
}
