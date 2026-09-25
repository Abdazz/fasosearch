import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { translate } from "./i18n";
import type { Lang } from "./types";

export type Theme = "nuit" | "faso";
interface Prefs { theme: Theme; setTheme: (t: Theme) => void; lang: Lang; setLang: (l: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string }

const Ctx = createContext<Prefs | null>(null);

function stored<T extends string>(key: string, allowed: T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key) as T | null;
    return v && allowed.includes(v) ? v : fallback;
  } catch { return fallback; }
}
function save(key: string, v: string) { try { localStorage.setItem(key, v); } catch { /* navigation privée */ } }

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => stored("fs.theme", ["nuit", "faso"], "faso"));
  const [lang, setLangState] = useState<Lang>(() => stored("fs.lang", ["fr", "en"], "fr"));
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const value: Prefs = {
    theme, lang,
    setTheme: (t) => { save("fs.theme", t); setThemeState(t); },
    setLang: (l) => { save("fs.lang", l); setLangState(l); },
    t: (key, vars) => translate(lang, key, vars),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePrefs(): Prefs {
  const v = useContext(Ctx);
  if (!v) throw new Error("PrefsProvider manquant");
  return v;
}
