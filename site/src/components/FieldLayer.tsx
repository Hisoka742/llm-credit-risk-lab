import { useCalm } from "../lib/useCalm";
import { motion, useScroll, useTransform } from "motion/react";
import { lazy, Suspense, useMemo } from "react";
import { study } from "../data/study";
import { fieldCount } from "../lib/field";

// three.js is loaded after first paint: the page is readable before the field arrives.
const LoanField = lazy(() => import("./LoanField"));

/** Fixed full-page layer holding the loan field. It dims once the hero is left behind. */
export function FieldLayer() {
  const reduce = useCalm();
  const { scrollY } = useScroll();
  const opacity = useTransform(scrollY, [0, 700], [1, 0.5]);

  // One mote per loan on capable desktops. Phones and low-core machines get a sample of the
  // same field (same seed, same default share) so scrolling stays smooth.
  const count = useMemo(() => fieldCount(), []);

  return (
    <motion.div
      className="pointer-events-none fixed inset-0 z-0"
      style={{ opacity: reduce ? 0.6 : opacity }}
      aria-hidden="true"
    >
      <Suspense fallback={null}>
        <LoanField count={count} defaultRate={study.totals.default_rate} animate={!reduce} />
      </Suspense>
    </motion.div>
  );
}
