import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { usePrefs } from "../prefs";
import type { DocumentResponse, ModelId, QueryLang } from "../types";
import { fmtScore } from "../utils";
import Highlight from "./Highlight";
import ScoreRing from "./ScoreRing";
import UniBadge from "./UniBadge";

export default function DocumentPanel({ id, query, model, lang, onClose, onOpen }: {
  id: string; query: string; model: ModelId; lang: QueryLang; onClose: () => void; onOpen: (id: string) => void }) {
  const { t } = usePrefs();
  const [d, setD] = useState<DocumentResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const titleId = useId();

  useEffect(() => {
    // Garde contre les reponses obsoletes : si l'utilisateur ouvre un autre
    // document (ex. via "documents similaires") avant que la reponse
    // precedente n'arrive, on ignore cette derniere plutot que d'ecraser
    // l'etat avec des donnees qui ne correspondent plus a `id`.
    let alive = true;
    setD(null); setErr(null);
    api.document(id, query, model, lang)
      .then((r) => { if (alive) setD(r); })
      .catch((e) => { if (alive) setErr(e.message); });
    return () => { alive = false; };
  }, [id, query, model, lang]);

  // Accessibilite : le focus entre dans le panneau a l'ouverture et revient
  // sur l'element qui l'a ouvert (carte de resultat, bouton "document similaire"...) a la fermeture.
  useEffect(() => {
    openerRef.current = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    return () => { openerRef.current?.focus(); };
  }, []);

  // Empeche le defilement de la page derriere le panneau (molette/tactile
  // au-dessus du voile) tant que le panneau est ouvert.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !panelRef.current) return;
      const focusables = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Le modele qui a reellement produit l'explication (peut differer du modele
  // courant de l'URL si celui-ci a change depuis l'ouverture du panneau) :
  // c'est lui qui doit piloter l'anneau de score et le format des nombres.
  const explModel = d?.explanation?.model ?? model;
  const maxC = Math.max(...(d?.explanation?.contributions.map((c) => c.value) ?? [1]), 1e-9);

  return (
    <div className="dp-veil" onClick={onClose}>
      <aside className="dp" ref={panelRef} tabIndex={-1} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true"
        aria-labelledby={d ? titleId : undefined} aria-label={d ? undefined : t("common.loading")}>
        <button className="btn dp-close" onClick={onClose}>✕ {t("detail.close")}</button>
        {err && <p className="dp-err">{err}</p>}
        {!d && !err && <div className="spinner" />}
        {d && (<>
          <div className="label">{d.document.id}</div>
          <h2 className="dp-title" id={titleId}>{d.document.title}</h2>
          <p className="dp-authors">{d.document.authors}</p>
          <div className="dp-meta"><UniBadge name={d.document.university} />{d.document.year && <span>{d.document.year}</span>}
            {d.document.url && <a className="btn" href={d.document.url} target="_blank" rel="noreferrer">↗ {t("detail.open")}</a>}</div>
          <p className="dp-abstract"><Highlight segments={d.document.abstract} /></p>

          <h3 className="dp-h">{t("detail.why")}</h3>
          {!d.explanation && <p className="dp-muted">{t("detail.noQuery")}</p>}
          {d.explanation && (
            <div className="dp-why panel">
              <ScoreRing value={d.explanation.score} ratio={1} model={explModel} size={96} />
              <div className="dp-bars">
                {explModel === "w2v" && <p className="dp-muted">{t("detail.w2vExplain")}</p>}
                {d.explanation.contributions.map((c) => (
                  <div key={c.term} className="dp-bar">
                    <span className="mono">{c.term}</span>
                    <div className="track"><div className="fill" style={{ width: `${(c.value / maxC) * 100}%` }} /></div>
                    <b className="mono">{fmtScore(c.value, explModel)}</b>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(d.neighbors).length > 0 && (<>
            <h3 className="dp-h">{t("detail.neighbors")}</h3>
            <div className="dp-neigh">
              {Object.entries(d.neighbors).map(([term, ns]) => (
                <div key={term}><span className="tok">{term}</span> →
                  {ns.length === 0 ? <span className="dp-muted"> ∅</span> :
                    ns.map((n) => <span key={n.word} className="nb">{n.word}<small>{n.similarity.toFixed(2)}</small></span>)}
                </div>
              ))}
            </div>
          </>)}

          <h3 className="dp-h">{t("detail.similar")}</h3>
          <div className="dp-sim">
            {d.similar.map((s) => (
              <button key={s.id} className="dp-simcard" onClick={() => onOpen(s.id)}>
                <span>{s.title}</span><small>{s.university.split(";")[0]} · {s.year} · cos {s.similarity.toFixed(2)}</small>
              </button>
            ))}
          </div>
        </>)}
      </aside>
      <style>{`
        .dp-veil{position:fixed;inset:0;z-index:50;background:rgba(5,6,16,.45);backdrop-filter:blur(3px);animation:fadeIn .25s both}
        @keyframes fadeIn{from{opacity:0}}
        .dp{position:absolute;top:0;right:0;bottom:0;width:min(580px,100%);overflow-y:auto;padding:26px 30px 48px;background:var(--bg);border-left:var(--border-w) solid var(--line-strong);animation:slideIn .4s var(--ease-out) both;display:flex;flex-direction:column;gap:14px}
        .dp:focus{outline:none}
        @keyframes slideIn{from{transform:translateX(40px);opacity:0}}
        .dp-close{align-self:flex-end}
        .dp-title{font:800 26px/1.2 var(--font-display);letter-spacing:-.02em}
        .dp-authors{color:var(--ink-2);font-size:14px}
        .dp-meta{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:14px;color:var(--ink-2)}
        .dp-abstract{font-size:15.5px;line-height:1.75;color:var(--ink-2)}
        .dp-h{font:700 16px var(--font-display);margin-top:10px}
        .dp-muted{color:var(--ink-3);font-size:14px}
        .dp-why{display:flex;gap:20px;align-items:center;padding:18px}
        .dp-bars{flex:1;display:flex;flex-direction:column;gap:9px}
        .dp-bar{display:grid;grid-template-columns:110px 1fr 54px;gap:10px;align-items:center;font-size:13px}
        .track{height:8px;border-radius:6px;background:var(--ring-track);overflow:hidden}
        .fill{height:100%;border-radius:6px;background:var(--grad);animation:grow .9s var(--ease-out) both;transform-origin:left}
        @keyframes grow{from{transform:scaleX(0)}}
        .mono{font-family:var(--font-mono)}
        .dp-neigh{display:flex;flex-direction:column;gap:10px;font-size:14px}
        .nb{display:inline-flex;gap:4px;align-items:baseline;margin-left:8px;padding:3px 9px;border-radius:999px;border:1px solid var(--line);font:500 12.5px var(--font-mono)}
        .nb small{color:var(--ink-3);font-size:10.5px}
        .dp-sim{display:flex;flex-direction:column;gap:8px}
        .dp-simcard{text-align:left;border:var(--border-w) solid var(--line);background:var(--surface);border-radius:14px;padding:12px 14px;display:flex;flex-direction:column;gap:4px;font-weight:600;font-size:14px}
        .dp-simcard:hover{border-color:var(--line-strong)}
        .dp-simcard small{font-weight:400;color:var(--ink-3);font-size:12.5px}
        .dp-err{color:var(--danger)}
        @media (max-width:640px){.dp{width:100%;border-left:0}}
      `}</style>
    </div>
  );
}
