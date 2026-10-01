import { useCalm } from "../lib/useCalm";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { EASE_OUT } from "../lib/motion";

type Props = { children: ReactNode; delay?: number; className?: string; y?: number };

/**
 * Enter-on-scroll for headings and prose. Content is visible by default: without JS, or
 * under reduced motion, nothing is hidden.
 */
export function Reveal({ children, delay = 0, className, y = 22 }: Props) {
  const reduce = useCalm();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.75, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}
