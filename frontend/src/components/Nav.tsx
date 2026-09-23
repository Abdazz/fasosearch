import { usePrefs } from "../prefs";
import { navigate, type Page } from "../router";

export default function Nav({ page }: { page: Page }) {
  const { t, theme, setTheme, lang, setLang } = usePrefs();
  const links: { id: Page; key: string }[] = [
    { id: "search", key: "nav.search" }, { id: "compare", key: "nav.compare" },
    { id: "lab", key: "nav.lab" }, { id: "corpus", key: "nav.corpus" },
  ];
  return (
    <nav className="nav">
      <button className="logo" onClick={() => navigate("home")} aria-label="FasoSearch">
        <span className="logo-mark">✦</span>Faso<b className="grad-text">Search</b>
      </button>
      <div className="links">
        {links.map((l) => (
          <button key={l.id} className={page === l.id || (page === "home" && l.id === "search") ? "on" : ""}
            onClick={() => navigate(l.id === "search" ? "home" : l.id)}>{t(l.key)}</button>
        ))}
      </div>
      <div className="tools">
        <button className="btn lang" onClick={() => setLang(lang === "fr" ? "en" : "fr")} aria-label="Langue / Language">
          <b className={lang === "fr" ? "" : "dim"}>FR</b><span className="dim">/</span><b className={lang === "en" ? "" : "dim"}>EN</b>
        </button>
        <button className="btn" onClick={() => setTheme(theme === "nuit" ? "faso" : "nuit")}>
          {theme === "nuit" ? `☀ ${t("theme.faso")}` : `☾ ${t("theme.nuit")}`}
        </button>
      </div>
      <style>{`
        .nav{display:flex;align-items:center;gap:28px;padding:22px 0;flex-wrap:wrap}
        .logo{border:0;background:none;font-family:var(--font-display);font-weight:800;font-size:23px;letter-spacing:-.02em;display:flex;align-items:center;gap:10px}
        .logo-mark{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:var(--grad);color:#fff;font-size:15px}
        [data-theme="faso"] .logo-mark{border:1.5px solid var(--ink);box-shadow:2px 2px 0 var(--ink)}
        .links{display:flex;gap:4px;font-size:14.5px;color:var(--ink-2)}
        .links button{border:0;background:none;padding:8px 15px;border-radius:999px;font-weight:500}
        .links button:hover{color:var(--ink)}
        .links button.on{color:var(--ink);background:var(--surface-2)}
        .tools{margin-left:auto;display:flex;gap:8px}
        .lang .dim{color:var(--ink-3);font-weight:500}
        @media (max-width:760px){.links{order:3;width:100%;overflow-x:auto}}
      `}</style>
    </nav>
  );
}
