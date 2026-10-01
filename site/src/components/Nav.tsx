import { List, X } from "@phosphor-icons/react";
import { motion, useMotionValueEvent, useScroll } from "motion/react";
import { useState } from "react";
import { EASE_OUT } from "../lib/motion";

const LINKS = [
  { href: "#voices", label: "Voices" },
  { href: "#method", label: "Method" },
  { href: "#results", label: "Results" },
  { href: "#limits", label: "Limits" },
];

export function Nav() {
  const { scrollY } = useScroll();
  // A single boolean flip, not a continuous value: fine as React state.
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useMotionValueEvent(scrollY, "change", (v) => setScrolled(v > 40));
  const solid = scrolled || open;

  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-40"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: EASE_OUT }}
    >
      <div
        className={`mx-auto flex h-16 max-w-[1400px] items-center justify-between px-5 transition-[background-color,backdrop-filter,border-color] duration-300 md:px-10 ${
          solid ? "border-b border-line bg-ink/80 backdrop-blur-xl" : "border-b border-transparent"
        }`}
      >
        <a href="#top" className="font-display text-lg font-medium" onClick={() => setOpen(false)}>
          LLM Credit Risk Lab
        </a>

        <nav aria-label="Sections" className="hidden md:block">
          <ul className="flex items-center gap-1 text-sm">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  className="rounded-full px-3.5 py-2 text-muted transition-colors duration-200 hover:text-paper"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Phone: the same four sections behind one menu button. */}
        <button
          type="button"
          className="btn btn-ghost !h-11 !w-11 justify-center !px-0 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-sections"
          aria-label={open ? "Close section menu" : "Open section menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={18} aria-hidden="true" /> : <List size={18} aria-hidden="true" />}
        </button>
      </div>

      {open && (
        <nav
          id="mobile-sections"
          aria-label="Sections"
          className="border-b border-line bg-ink/95 px-5 pb-4 pt-2 backdrop-blur-xl md:hidden"
        >
          <ul>
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  className="block py-3 font-display text-2xl font-medium"
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </motion.header>
  );
}
