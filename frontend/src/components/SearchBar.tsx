import { useEffect, useRef, useState } from "react";
import { usePrefs } from "../prefs";
import type { Lang, QueryLang, SearchMode } from "../types";

interface Props {
  initial?: string; lang: QueryLang; detected?: { language: Lang; forced: boolean } | null;
  onSubmit: (q: string) => void; onLangChange: (l: QueryLang) => void; big?: boolean;
  mode?: SearchMode; onModeChange?: (m: SearchMode) => void;
}
const NEXT: Record<QueryLang, QueryLang> = { auto: "fr", fr: "en", en: "auto" };

export default function SearchBar({ initial = "", lang, detected, onSubmit, onLangChange, big, mode = "papers", onModeChange }: Props) {
  const { t } = usePrefs();
  const [q, setQ] = useState(initial);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => setQ(initial), [initial]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement !== input.current) { e.preventDefault(); input.current?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  let badge = t("search.auto");
  if (lang !== "auto") badge = t("search.forced", { lang: lang.toUpperCase() });
  else if (detected) badge = t("search.detected", { lang: detected.language.toUpperCase() });
  const showArrow = (lang === "fr") || (lang === "auto" && detected?.language === "fr");
  const authors = mode === "authors";
  const placeholder = t(authors ? "search.authorPlaceholder" : "search.placeholder");

  return (
    <div className="search-wrap">
      {onModeChange && (
        <div className="mode-switch" role="group" aria-label={t("search.mode.label")}>
          {(["papers", "authors"] as const).map((m) => (
            <button key={m} type="button" className={mode === m ? "on" : ""} aria-pressed={mode === m}
              onClick={() => onModeChange(m)}>{t(`search.mode.${m}`)}</button>
          ))}
        </div>
      )}
      <form className={`search ${big ? "search-big" : ""}`} onSubmit={(e) => { e.preventDefault(); if (q.trim()) onSubmit(q.trim()); }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder}
          aria-label={placeholder} autoFocus={big} />
        {!authors && (
          <button type="button" className="detect" title={t("search.langHint")} onClick={() => onLangChange(NEXT[lang])}>
            {badge} {showArrow && t("search.toEn")}
          </button>
        )}
        <button type="submit" className="go">{t("search.go")}</button>
      </form>
      <style>{`
        .search{display:flex;align-items:center;gap:14px;padding:8px 8px 8px 22px;border-radius:var(--search-radius);background:var(--surface);border:var(--border-w) solid var(--line-strong);box-shadow:var(--shadow);backdrop-filter:var(--blur)}
        .search svg{flex:none;color:var(--ink-3)}
        .search input{flex:1;min-width:0;background:none;border:0;outline:0;color:var(--ink);font:500 19px var(--font-body)}
        .search input::placeholder{color:var(--ink-3)}
        .search-big{padding:12px 12px 12px 26px}.search-big input{font-size:21px}
        .detect{font:600 11px var(--font-mono);letter-spacing:.04em;padding:6px 11px;border-radius:999px;background:var(--chip);color:var(--chip-ink);border:0;white-space:nowrap}
        .go{height:48px;padding:0 26px;border:0;border-radius:16px;background:var(--active-bg);color:var(--on-accent);font:700 15px var(--font-display)}
        [data-theme="faso"] .go{border-radius:999px}
        .mode-switch{display:inline-flex;gap:4px;padding:4px;margin-bottom:10px;border-radius:999px;background:var(--surface);border:var(--border-w) solid var(--line)}
        .mode-switch button{border:0;background:none;padding:6px 16px;border-radius:999px;font:600 13px var(--font-body);color:var(--ink-2)}
        .mode-switch button.on{background:var(--active-bg);color:var(--on-accent)}
        @media (max-width:760px){.detect{display:none}.go{padding:0 16px}}
      `}</style>
    </div>
  );
}
