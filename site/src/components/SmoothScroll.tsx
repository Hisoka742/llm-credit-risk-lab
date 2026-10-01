import { useCalm } from "../lib/useCalm";
import Lenis from "lenis";
import { useEffect } from "react";

const NAV_OFFSET = -72;

/**
 * Lenis smooth scrolling plus in-page anchor handling. Under reduced motion Lenis is not
 * started at all and anchors jump natively.
 */
export function SmoothScroll() {
  const reduce = useCalm();

  // Deep links: the page mounts after the browser has already looked for the anchor, so a
  // link like /#results would otherwise land at the top. Jump there once content exists.
  useEffect(() => {
    const id = window.location.hash;
    if (id.length < 2) return;
    const target = document.querySelector<HTMLElement>(id);
    if (target) window.scrollTo({ top: target.offsetTop + NAV_OFFSET, behavior: "instant" });
  }, []);

  useEffect(() => {
    if (reduce) return;
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
    let frame = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      frame = requestAnimationFrame(raf);
    };
    frame = requestAnimationFrame(raf);

    const onClick = (e: MouseEvent) => {
      const link = (e.target as HTMLElement | null)?.closest<HTMLAnchorElement>('a[href^="#"]');
      if (!link) return;
      const id = link.getAttribute("href");
      if (!id || id === "#") return;
      const target = document.querySelector<HTMLElement>(id);
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target, { offset: NAV_OFFSET });
      history.replaceState(null, "", id);
    };
    document.addEventListener("click", onClick);

    return () => {
      document.removeEventListener("click", onClick);
      cancelAnimationFrame(frame);
      lenis.destroy();
    };
  }, [reduce]);

  return null;
}
