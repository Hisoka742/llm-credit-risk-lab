import { List, X } from "@phosphor-icons/react";
import { motion, useMotionValueEvent, useScroll } from "motion/react";
import { useState } from "react";
import { useLang } from "../lib/i18n";
import { EASE_OUT } from "../lib/motion";

const LINKS = [
  { href: "#voices", en: "Voices", ru: "Голоса" },
  { href: "#method", en: "Method", ru: "Метод" },
  { href: "#results", en: "Results", ru: "Результаты" },
  { href: "#live", en: "Live", ru: "Вживую" },
  { href: "#limits", en: "Limits", ru: "Ограничения" },
];

/** Switches the page language. The label names the language it switches to, in that language. */
function LangToggle({ className = "" }: { className?: string }) {
  const { lang, setLang } = useLang();
  const next = lang === "ru" ? "en" : "ru";
  return (
    <button
      type="button"
      lang={next}
      onClick={() => setLang(next)}
      aria-label={next === "ru" ? "Переключить на русский" : "Switch to English"}
      className={`tnum rounded-full border border-paper/30 px-3 py-1.5 text-sm font-medium text-paper transition-colors duration-200 hover:border-paper/60 hover:bg-paper/[0.06] ${className}`}
    >
      {next === "ru" ? "RU" : "EN"}
    </button>
  );
}

export function Nav() {
  const { t, ru } = useLang();
  const { scrollY } = useScroll();
  // A single boolean flip, not a continuous value: fine as React state.
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useMotionValueEvent(scrollY, "change", (v) => setScrolled(v > 40));
  const solid = scrolled || open;
  const sections = t("Sections", "Разделы");

  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-40"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: EASE_OUT }}
    >
      <div
        className={`mx-auto flex h-16 max-w-[1400px] items-center justify-between gap-3 px-5 transition-[background-color,backdrop-filter,border-color] duration-300 md:px-10 ${
          solid ? "border-b border-line bg-ink/80 backdrop-blur-xl" : "border-b border-transparent"
        }`}
      >
        <a href="#top" className="font-display text-lg font-medium" onClick={() => setOpen(false)}>
          LLM Credit Risk Lab
        </a>

        <nav aria-label={sections} className="hidden md:block">
          <ul className="flex items-center gap-1 text-sm">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  className="rounded-full px-3.5 py-2 text-muted transition-colors duration-200 hover:text-paper"
                >
                  {ru ? l.ru : l.en}
                </a>
              </li>
            ))}
            <li className="ml-2">
              <LangToggle />
            </li>
          </ul>
        </nav>

        {/* Phone: the language switch stays visible, the sections sit behind one menu button. */}
        <div className="flex items-center gap-2 md:hidden">
          <LangToggle />
          <button
            type="button"
            className="btn btn-ghost !h-11 !w-11 justify-center !px-0"
            aria-expanded={open}
            aria-controls="mobile-sections"
            aria-label={open ? t("Close section menu", "Закрыть меню разделов") : t("Open section menu", "Открыть меню разделов")}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={18} aria-hidden="true" /> : <List size={18} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="mobile-sections"
          aria-label={sections}
          className="border-b border-line bg-ink/95 px-5 pb-4 pt-2 backdrop-blur-xl md:hidden"
        >
          <ul>
            {LINKS.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="block py-3 font-display text-2xl font-medium" onClick={() => setOpen(false)}>
                  {ru ? l.ru : l.en}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </motion.header>
  );
}
