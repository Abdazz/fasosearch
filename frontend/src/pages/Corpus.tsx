import { useEffect, useMemo, useState } from "react";
import EmptyState from "../components/EmptyState";
import UniBadge from "../components/UniBadge";
import { ApiError, api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { CorpusResponse } from "../types";
import { useUniColor } from "../uniColors";
import { fmtNum, uniColor } from "../utils";

export default function Corpus() {
  const { t, lang } = usePrefs();
  useUniColor();
  const [data, setData] = useState<CorpusResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [uni, setUni] = useState("");
  const [year, setYear] = useState("");
  // Infobulle des barres "par année" en position fixe (et non ancrée en CSS à la
  // barre) : le graphique défile horizontalement, donc une infobulle ancrée en
  // CSS pur serait tronquée par le conteneur pour les barres proches d'un bord
  // du viewport de défilement, quelle que soit sa position. `position: fixed`,
  // calculée depuis `getBoundingClientRect()`, échappe à ce rognage.
  const [yearTip, setYearTip] = useState<{ x: number; y: number; label: string } | null>(null);

  useEffect(() => {
    let alive = true;
    api.corpus()
      .then((d) => { if (alive) { setData(d); setErr(null); } })
      .catch((e: ApiError) => { if (alive) setErr(e.message); });
    return () => { alive = false; };
  }, []);

  // Masque l'infobulle plutôt que de la repositionner si la page (ou le
  // graphique lui-même) défile ou si la fenêtre est redimensionnée pendant
  // qu'elle est affichée : ses coordonnées, capturées une fois au survol/focus,
  // deviendraient sinon obsolètes. Écouteurs ajoutés seulement pendant que
  // l'infobulle est ouverte, retirés à sa fermeture ou au démontage.
  useEffect(() => {
    if (!yearTip) return;
    const hide = () => setYearTip(null);
    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", hide);
    return () => {
      window.removeEventListener("scroll", hide, true);
      window.removeEventListener("resize", hide);
    };
  }, [yearTip]);

  const rows = useMemo(() => (data?.documents ?? []).filter((d) =>
    (!q || `${d.title} ${d.authors}`.toLowerCase().includes(q.toLowerCase())) &&
    (!uni || d.university.split(";").map((s) => s.trim()).includes(uni)) &&
    (!year || String(d.year) === year)), [data, q, uni, year]);

  const openDoc = (id: string, title: string) => navigate("search", { q: title, doc: id });

  if (err) return <EmptyState kind={err === "server_down" ? "server_down" : "error"} msg={err} />;
  if (!data) return <div className="spinner" />;
  const maxU = Math.max(...data.universities.map((u) => u.count), 1);
  const maxY = Math.max(...data.years.map((y) => y.count), 1);

  return (
    <section className="corpus">
      <h1 className="h-display lab-h">{t("corpus.title")}</h1>
      <p className="lab-sub">{t("corpus.subtitle", { n: data.documents.length })}</p>
      <p className="lab-muted corpus-stats">{t("corpus.stats", {
        n: fmtNum(data.documents.length, lang), u: fmtNum(data.universities.length, lang), v: fmtNum(data.vocabulary_size, lang),
      })}</p>
      <div className="corpus-charts">
        <div className="panel lab-block">
          <h3 className="lab-h3">{t("corpus.byUni")}</h3>
          {data.universities.slice(0, 10).map((u, i) => (
            <button key={u.name} className="hbar" title={u.name} aria-pressed={uni === u.name}
              onClick={() => setUni(uni === u.name ? "" : u.name)} style={{ opacity: uni && uni !== u.name ? .45 : 1 }}>
              <span className="hbar-l">{u.name}</span>
              <span className="hbar-t"><span style={{ width: `${(u.count / maxU) * 100}%`, background: uniColor(u.name), animationDelay: `${i * .05}s` }} /></span>
              <b className="mono">{u.count}</b>
            </button>))}
        </div>
        <div className="panel lab-block">
          <h3 className="lab-h3">{t("corpus.byYear")}</h3>
          <div className="vbars">
            {data.years.map((y, i) => {
              const yearLabel = t("corpus.year.aria", { y: y.year, n: y.count });
              const showTip = (e: { currentTarget: HTMLButtonElement }) => {
                const r = e.currentTarget.getBoundingClientRect();
                setYearTip({ x: r.left + r.width / 2, y: r.top, label: yearLabel });
              };
              return (
                <button key={y.year} className="vbar" aria-pressed={year === String(y.year)}
                  onClick={() => setYear(year === String(y.year) ? "" : String(y.year))}
                  style={{ opacity: year && year !== String(y.year) ? .45 : 1 }}
                  aria-label={yearLabel}
                  onMouseEnter={showTip} onFocus={showTip}
                  onMouseLeave={() => setYearTip(null)} onBlur={() => setYearTip(null)}>
                  <b className="mono" aria-hidden="true">{y.count}</b>
                  <span style={{ height: `${(y.count / maxY) * 150}px`, animationDelay: `${i * .04}s` }} />
                  <small aria-hidden="true">{String(y.year).slice(2)}</small>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      {/* Rendue hors de tout ancêtre `.panel` : `backdrop-filter` y crée un bloc
          conteneur pour les descendants en `position: fixed`, ce qui décalerait
          l'infobulle (elle serait positionnée par rapport au panneau, pas à la
          fenêtre) et fausserait les coordonnées calculées via getBoundingClientRect(). */}
      {yearTip && <div className="year-tip" style={{ left: yearTip.x, top: yearTip.y }}>{yearTip.label}</div>}
      <div className="corpus-filters">
        <input className="lab-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("corpus.filter")} aria-label={t("corpus.filter")} />
        <select value={uni} onChange={(e) => setUni(e.target.value)} aria-label={t("corpus.allUnis")}>
          <option value="">{t("corpus.allUnis")}</option>{data.universities.map((u) => <option key={u.name}>{u.name}</option>)}</select>
        <select value={year} onChange={(e) => setYear(e.target.value)} aria-label={t("corpus.allYears")}>
          <option value="">{t("corpus.allYears")}</option>{data.years.map((y) => <option key={y.year}>{y.year}</option>)}</select>
      </div>
      <div className="panel table-wrap">
        <table>
          <thead><tr><th>{t("corpus.col.id")}</th><th>{t("corpus.col.title")}</th><th>{t("corpus.col.uni")}</th><th>{t("corpus.col.year")}</th></tr></thead>
          <tbody>{rows.map((d) => (
            <tr key={d.id} tabIndex={0} role="button" aria-label={t("corpus.row.open", { id: d.id })}
              onClick={() => openDoc(d.id, d.title)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDoc(d.id, d.title); } }}>
              <td className="mono">{d.id.replace("Document_", "#")}</td>
              <td><b>{d.title}</b><small>{d.authors}</small></td>
              <td>{d.university ? <UniBadge name={d.university} /> : <span className="lab-muted">{t("common.uniUnknown")}</span>}</td>
              <td className="mono">{d.year ?? "?"}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <style>{`
        .corpus{padding-top:22px;display:flex;flex-direction:column;gap:16px}
        .corpus-charts{display:grid;grid-template-columns:1.3fr 1fr;gap:16px}
        .corpus-charts>.panel{min-width:0}
        .hbar{display:grid;grid-template-columns:minmax(0,210px) 1fr 34px;gap:10px;align-items:center;border:0;background:none;text-align:left;font-size:13px;padding:4px 0}
        .hbar-l{line-height:1.25;overflow-wrap:anywhere}
        .hbar-t{height:12px;border-radius:6px;background:var(--ring-track);overflow:hidden}
        .hbar-t span{display:block;height:100%;border-radius:6px;animation:grow .9s var(--ease-out) both;transform-origin:left}
        @keyframes growY{from{transform:scaleY(0)}}
        .vbars{display:flex;align-items:flex-end;gap:8px;height:200px;overflow-x:auto}
        .vbar{flex:1;min-width:26px;border:0;background:none;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;font-size:11px}
        .vbar span{width:100%;border-radius:6px 6px 2px 2px;background:var(--grad);animation:growY .9s var(--ease-out) both;transform-origin:bottom}
        .vbar small{color:var(--ink-3);font-family:var(--font-mono)}
        .year-tip{position:fixed;transform:translate(-50%,calc(-100% - 8px));background:var(--surface-solid);color:var(--ink);font:600 11.5px var(--font-mono);padding:5px 9px;border-radius:8px;white-space:nowrap;pointer-events:none;z-index:50;box-shadow:var(--card-shadow)}
        .corpus-stats{margin-top:-6px}
        .corpus-filters{display:grid;grid-template-columns:1fr 260px 170px;gap:10px}
        .corpus-filters select{width:100%;background:var(--surface);border:var(--border-w) solid var(--line);border-radius:14px;padding:12px 14px;color:var(--ink);font:500 15px var(--font-body)}
        .table-wrap{overflow-x:auto;padding:6px}
        table{width:100%;border-collapse:collapse;font-size:14px}
        th{text-align:left;font:600 11px var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);padding:12px}
        td{padding:12px;border-top:1px solid var(--line);vertical-align:top}
        td small{display:block;color:var(--ink-3);font-size:12.5px;margin-top:3px}
        tbody tr{cursor:pointer;transition:background .15s}tbody tr:hover{background:var(--surface-2)}
        @media (max-width:900px){.corpus-charts,.corpus-filters{grid-template-columns:1fr}}
      `}</style>
    </section>
  );
}
