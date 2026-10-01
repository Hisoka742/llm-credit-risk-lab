import { useReducedMotion } from "motion/react";

const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;

// `?capture` forces the reduced-motion path, so screenshots and visual review see settled
// content. It exercises exactly the fallback real users get when their system asks for
// reduced motion.
const CAPTURE = Boolean(params?.has("capture"));

// `?motion=on` shows the animated site even when the operating system has animations turned
// off (Windows: Settings > Accessibility > Visual effects > Animation effects). It is a
// preview aid for the site's owner: visitors always get what their own system asks for.
const FORCE_MOTION = params?.get("motion") === "on";

/** True when motion should be skipped: system preference or capture mode. */
export function useCalm(): boolean {
  const reduce = useReducedMotion();
  if (CAPTURE) return true;
  if (FORCE_MOTION) return false;
  return Boolean(reduce);
}
