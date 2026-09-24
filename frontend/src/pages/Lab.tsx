import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { MapPoint, NeighborsResponse, PreprocessResponse } from "../types";
import { uniAbbr, uniColor } from "../utils";

export default function Lab() {
  const { t } = usePrefs();
  const [text, setText] = useState(() => t("lab.sample"));
  const [mode, setMode] = useState<"lemma" | "stem">("lemma");
  const [pre, setPre] = useState<PreprocessResponse | null>(null);
  const [word, setWord] = useState("intrusion");
  const [nb, setNb] = useState<NeighborsResponse | null>(null);
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [hover, setHover] = useState<MapPoint | null>(null);

  // Prétraitement : débouncé, avec garde "alive" pour ignorer une réponse
  // devenue obsolète si le texte ou le mode change avant qu'elle n'arrive.
  useEffect(() => {
    let alive = true;
    const h = setTimeout(() => {
      api.preprocess(text, mode)
        .then((r) => { if (alive) setPre(r); })
        .catch(() => { if (alive) setPre(null); });
    }, 250);
    return () => { alive = false; clearTimeout(h); };
  }, [text, mode]);

  // Voisins Word2Vec : même garde, et on efface le résultat précédent si le
  // champ est vidé plutôt que de laisser un état obsolète affiché.
  useEffect(() => {
    const w = word.trim();
    if (!w) { setNb(null); return; }
    let alive = true;
    const h = setTimeout(() => {
      api.neighbors(w)
        .then((r) => { if (alive) setNb(r); })
        .catch(() => { if (alive) setNb(null); });
    }, 300);
    return () => { alive = false; clearTimeout(h); };
  }, [word]);

  useEffect(() => {
    let alive = true;
    api.map()
      .then((m) => { if (alive) setPoints(m.points); })
      .catch(() => { if (alive) setPoints([]); });
    return () => { alive = false; };
  }, []);

  const tokens = pre?.tokens ?? [];
  type Item = { text: string; cls: string; why?: string };
  const steps: { key: string; items: Item[] }[] = [
    { key: "lab.step1", items: tokens.map((tk) => ({ text: tk.raw, cls: "" })) },
    { key: "lab.step2", items: tokens.map((tk) => ({ text: tk.normalized ?? tk.raw,
        cls: tk.removed_by === "punctuation" || tk.removed_by === "number" ? "x" : "",
        why: tk.removed_by === "punctuation" || tk.removed_by === "number" ? t(`lab.removed.${tk.removed_by}`) : undefined })) },
    { key: "lab.step3", items: tokens.filter((tk) => tk.normalized).map((tk) => ({ text: tk.normalized!,
        cls: tk.removed_by === "stopword" ? "x" : "", why: tk.removed_by === "stopword" ? t("lab.removed.stopword") : undefined })) },
    { key: mode === "lemma" ? "lab.step4.lemma" : "lab.step4.stem", items: tokens.filter((tk) => tk.term).map((tk) => ({
        text: tk.term!, cls: tk.term !== tk.normalized ? "chg" : "",
        why: tk.term !== tk.normalized ? t("lab.changedFrom", { w: tk.normalized ?? "" }) : undefined })) },
  ];
  const unis = useMemo(() => [...new Set(points.map((p) => p.university).filter(Boolean))], [points]);
  const uniLabel = (name: string) => name || t("common.uniUnknown");
  const openPoint = (p: MapPoint) => navigate("search", { q: p.title, model: "w2v", doc: p.id });

  return (
    <section className="lab">
      <h1 className="h-display lab-h">{t("lab.title")}</h1>
      <p className="lab-sub">{t("lab.subtitle")}</p>

      <div className="panel lab-block">
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={t("lab.input")} rows={3} aria-label={t("lab.input")} />
        <div className="lab-mode"><span className="label">{t("lab.mode")}</span>
          {(["lemma", "stem"] as const).map((m) => (
            <button key={m} className={`btn ${mode === m ? "btn-primary" : ""}`} onClick={() => setMode(m)} aria-pressed={mode === m}>
              {t(m === "lemma" ? "lab.step4.lemma" : "lab.step4.stem")}</button>))}
        </div>
        <ol className="lab-steps">
          {steps.map((s, i) => (
            <li key={s.key} className="fade-up" style={{ animationDelay: `${i * 0.12}s` }}>
              <span className="lab-n" aria-hidden="true">{i + 1}</span><span className="label">{t(s.key)}</span>
              <div className="lab-toks">{s.items.map((it, j) => (
                <span key={j} className={`tok ${it.cls}`} title={it.why}>{it.text}{it.why && it.cls === "chg" && <small>{it.why}</small>}</span>))}</div>
            </li>
          ))}
        </ol>
        <div className="lab-result"><span className="label">{t("lab.termsLabel")}</span>
          <code className="mono">[{pre?.terms.map((x) => `"${x}"`).join(", ")}]</code></div>
      </div>

      <div className="lab-two">
        <div className="panel lab-block">
          <h3 className="lab-h3">{t("lab.formulas")}</h3>
          <div className="formula"><b>TF</b><span>tf(t,d) / max<sub>t'</sub> tf(t',d)</span></div>
          <div className="formula"><b>IDF</b><span>log( N / df(t) )</span></div>
          <div className="formula"><b>w</b><span>TF(t,d) × IDF(t)</span></div>
          <div className="formula"><b>cos</b><span>(q · d) / (‖q‖ ‖d‖)</span></div>
          <div className="formula"><b>W2V</b><span>v(d) = Σ idf(t)·v(t) / Σ idf(t)</span></div>
          <div className="formula"><b>BM25</b><span>Σ IDF(t) · tf·(k₁+1) / (tf + k₁(1−b+b·|d|/avgdl))</span></div>
        </div>
        <div className="panel lab-block">
          <h3 className="lab-h3">{t("lab.neighbors")}</h3>
          <input className="lab-input" value={word} onChange={(e) => setWord(e.target.value)} placeholder={t("lab.neighbors.input")} aria-label={t("lab.neighbors.input")} />
          {nb && !nb.in_vocabulary && <p className="lab-muted">{t("lab.neighbors.unknown", { w: nb.term })}</p>}
          <div className="lab-nb">{nb?.neighbors.map((n, i) => (
            <div key={n.word} className="lab-nbrow fade-up" style={{ animationDelay: `${i * 0.04}s` }}>
              <span className="mono">{n.word}</span>
              <div className="track"><div className="fill" style={{ width: `${Math.max(0, n.similarity) * 100}%` }} /></div>
              <b className="mono">{n.similarity.toFixed(3)}</b>
            </div>))}</div>
        </div>
      </div>

      <div className="panel lab-block">
        <h3 className="lab-h3">{t("lab.map")}</h3>
        <p className="lab-muted">{t("lab.map.subtitle")}</p>
        <div className="map">
          <svg viewBox="0 0 1000 520" preserveAspectRatio="none">
            {points.map((p, i) => (
              <circle key={p.id} cx={30 + p.x * 940} cy={20 + (1 - p.y) * 480} r={hover?.id === p.id ? 11 : 7}
                fill={uniColor(p.university)} fillOpacity={hover && hover.id !== p.id ? .35 : .9}
                stroke="var(--bg)" strokeWidth="2" style={{ animation: `pop .6s ${i * 0.01}s both`, cursor: "pointer", transition: "r .2s" }}
                tabIndex={0} role="button" aria-label={`${p.title} · ${uniLabel(p.university)} · ${p.year ?? ""}`}
                onMouseEnter={() => setHover(p)} onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(p)} onBlur={() => setHover(null)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPoint(p); } }}
                onClick={() => openPoint(p)} />
            ))}
          </svg>
          {hover && <div className="map-tip panel" style={{ left: `${3 + hover.x * 88}%`, top: `${(1 - hover.y) * 86}%` }}>
            <b>{hover.title}</b><small>{uniLabel(hover.university)} · {hover.year}</small></div>}
        </div>
        <div className="map-legend">{unis.map((u) => <span key={u}><i style={{ background: uniColor(u) }} />{uniAbbr(u)} <small>{u}</small></span>)}</div>
      </div>

      <style>{`
        .lab{padding-top:22px;display:flex;flex-direction:column;gap:16px}
        .lab textarea{width:100%;background:var(--surface-2);border:var(--border-w) solid var(--line);border-radius:14px;padding:14px 16px;color:var(--ink);font:500 16px var(--font-body);resize:vertical}
        .lab-mode{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
        .lab-steps{list-style:none;padding:0;display:flex;flex-direction:column;gap:12px}
        .lab-steps li{display:grid;grid-template-columns:32px 190px 1fr;gap:12px;align-items:start}
        .lab-n{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--active-bg);color:var(--on-accent);font:700 13px var(--font-mono)}
        .lab-toks{display:flex;flex-wrap:wrap;gap:6px}
        .tok{font:500 13px var(--font-mono);padding:4px 10px;border-radius:8px;background:var(--chip);color:var(--chip-ink);animation:pop .5s both}
        .tok.x{background:none;color:var(--ink-3);text-decoration:line-through;border:1px dashed var(--line)}
        .tok.chg{outline:1.5px solid var(--accent-2)}
        .tok small{opacity:.65;margin-left:6px;font-size:11px}
        .lab-result code{font:500 14px var(--font-mono);color:var(--accent-2);margin-left:10px;word-break:break-word}
        .lab-two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
        .lab-two>.panel{min-width:0}
        .formula{display:grid;grid-template-columns:70px 1fr;gap:10px;align-items:center;padding:10px 12px;border-radius:12px;background:var(--surface-2);font:500 14px var(--font-mono)}
        .formula b{color:var(--accent);font-family:var(--font-display)}
        .lab-nb{display:flex;flex-direction:column;gap:8px}
        .lab-nbrow{display:grid;grid-template-columns:140px 1fr 60px;gap:10px;align-items:center;font-size:13.5px}
        .map{position:relative;aspect-ratio:1000/520;min-height:260px;border-radius:14px;background:var(--surface-2);overflow:hidden}
        .map svg{width:100%;height:100%}
        .map svg circle:focus-visible{outline:3px solid var(--accent-2);outline-offset:1px}
        .map-tip{position:absolute;padding:10px 12px;max-width:320px;display:flex;flex-direction:column;gap:3px;font-size:13px;pointer-events:none;background:var(--surface-solid)}
        .map-tip small{color:var(--ink-3)}
        .map-legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13px}
        .map-legend span{display:flex;align-items:center;gap:6px;font-weight:600}
        .map-legend small{font-weight:400;color:var(--ink-3)}
        .map-legend i{width:11px;height:11px;border-radius:50%}
        @media (max-width:900px){.lab-two{grid-template-columns:1fr}.lab-steps li{grid-template-columns:32px 1fr}.lab-steps li .lab-toks{grid-column:1/-1}}
      `}</style>
    </section>
  );
}
