import { study } from "../data/study";

/**
 * How many motes the loan field draws. Capable desktops get one per loan; phones and
 * low-core machines get a seeded sample with the same default share, so scrolling stays
 * smooth. The hero key reads this too, so the page never claims more dots than it draws.
 */
export function fieldCount(): number {
  if (typeof window === "undefined") return 36000;
  const wide = window.matchMedia("(min-width: 900px)").matches;
  const cores = navigator.hardwareConcurrency ?? 4;
  return wide && cores >= 6 ? study.totals.loans : 36000;
}
