import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "ru";

const KEY = "lang";

// Order: an explicit ?lang= in the address, then the visitor's last choice, then the browser
// language. Storage can be unavailable (private windows), so every access is guarded.
function initialLang(): Lang {
  if (typeof window === "undefined") return "en";
  const q = new URLSearchParams(window.location.search).get("lang");
  if (q === "ru" || q === "en") return q;
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved === "ru" || saved === "en") return saved;
  } catch {
    /* fall through to the browser language */
  }
  return navigator.language?.toLowerCase().startsWith("ru") ? "ru" : "en";
}

type Ctx = { lang: Lang; ru: boolean; setLang: (l: Lang) => void; t: (en: string, ru: string) => string };

const LangContext = createContext<Ctx>({ lang: "en", ru: false, setLang: () => undefined, t: (en) => en });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      window.localStorage.setItem(KEY, l);
    } catch {
      /* the choice still holds for this visit */
    }
  }, []);

  const value = useMemo<Ctx>(
    () => ({ lang, ru: lang === "ru", setLang, t: (en, ru) => (lang === "ru" ? ru : en) }),
    [lang, setLang],
  );
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

/** `t("English", "Русский")` keeps both versions of a sentence side by side in the component. */
export const useLang = (): Ctx => useContext(LangContext);
