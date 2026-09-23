import { useEffect, useState } from "react";
import SearchBar from "../components/SearchBar";
import { api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { QueryLang, Stats } from "../types";

const EXAMPLES = ["détection d'intrusion dans les réseaux", "Internet exchange points in Africa",
  "apprentissage automatique pour la santé", "ontology for agriculture", "sécurité des sites web gouvernementaux"];

function Counter({ value }: { value: number }) {
  const { lang } = usePrefs();
  const [v, setV] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setV(value); return; }
    let raf = 0; const t0 = performance.now();
    const step = (t: number) => { const k = Math.min(1, (t - t0) / 1200); setV(Math.round(value * (1 - (1 - k) ** 3))); if (k < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{v.toLocaleString(lang === "fr" ? "fr-FR" : "en-US")}</>;
}

export default function Home() {
  const { t } = usePrefs();
  const [lang, setLang] = useState<QueryLang>("auto");
  const [stats, setStats] = useState<Stats | null>(null);
  useEffect(() => { api.stats().then(setStats).catch(() => setStats(null)); }, []);
  const go = (q: string) => navigate("search", { q, lang: lang === "auto" ? undefined : lang });

  return (
    <section className="home">
      <div className="label fade-up">{t("home.eyebrow")}</div>
      <h1 className="h-display fade-up" style={{ animationDelay: ".05s" }}>
        {t("home.tagline").split(",")[0]}<span className="grad-text">{t("home.tagline").includes(",") ? "," + t("home.tagline").split(",").slice(1).join(",") : ""}</span>
      </h1>
      <p className="sub fade-up" style={{ animationDelay: ".1s" }}>{t("home.subtitle")}</p>
      <div className="fade-up" style={{ animationDelay: ".15s" }}>
        <SearchBar big lang={lang} onLangChange={setLang} onSubmit={go} />
      </div>
      <div className="examples fade-up" style={{ animationDelay: ".2s" }}>
        <span className="label">{t("home.examples")}</span>
        {EXAMPLES.map((e) => <button key={e} className="ex" onClick={() => go(e)}>{e}</button>)}
      </div>
      {stats && (
        <div className="stats">
          {[["home.stat.documents", stats.documents], ["home.stat.universities", stats.universities],
            ["home.stat.vocabulary", stats.vocabulary]].map(([k, v], i) => (
            <div key={k} className="stat panel fade-up" style={{ animationDelay: `${.25 + i * .07}s` }}>
              <b className="h-display"><Counter value={v as number} /></b><span>{t(k as string)}</span>
            </div>
          ))}
          <div className="stat panel fade-up" style={{ animationDelay: ".46s" }}>
            <b className="h-display">{stats.year_min ?? "?"}-{stats.year_max ?? "?"}</b><span>{t("home.stat.years")}</span>
          </div>
        </div>
      )}
      <style>{`
        .home{padding:56px 0 24px;display:flex;flex-direction:column;gap:22px}
        .home h1{font-size:clamp(40px,6.4vw,76px);max-width:14ch}
        .home .sub{font-size:18px;line-height:1.6;color:var(--ink-2);max-width:62ch}
        .examples{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
        .ex{border:var(--border-w) solid var(--line);background:var(--surface);border-radius:999px;padding:7px 14px;font-size:13.5px;color:var(--ink-2)}
        .ex:hover{color:var(--ink);border-color:var(--line-strong)}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:22px}
        .stat{padding:20px 22px;display:flex;flex-direction:column;gap:6px;box-shadow:var(--card-shadow)}
        .stat b{font-size:40px}
        .stat span{color:var(--ink-2);font-size:14px}
        @media (max-width:760px){.stats{grid-template-columns:1fr 1fr}}
      `}</style>
    </section>
  );
}
