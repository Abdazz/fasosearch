import { usePrefs } from "../prefs";
import type { ModelId, SearchResult } from "../types";
import Highlight from "./Highlight";
import ScoreRing from "./ScoreRing";
import UniBadge from "./UniBadge";

function shortAuthors(a: string, etAl: string) {
  const list = a.split(";").map((s) => s.trim()).filter(Boolean);
  return list.length > 3 ? `${list.slice(0, 2).join(", ")} ${etAl}` : list.join(", ");
}

export default function ResultCard({ result, model, index, onOpen }: { result: SearchResult; model: ModelId; index: number; onOpen: (id: string) => void }) {
  const { t } = usePrefs();
  return (
    <article className="card" style={{ animationDelay: `${index * 0.06}s` }} tabIndex={0}
      onClick={() => onOpen(result.id)} onKeyDown={(e) => e.key === "Enter" && onOpen(result.id)}>
      <div className={`rank ${result.rank === 1 ? "grad-text" : ""}`}>{String(result.rank).padStart(2, "0")}</div>
      <div className="body">
        <h3 className="title">{result.title}</h3>
        <div className="byline">
          <span>{shortAuthors(result.authors, t("results.etAl"))}</span><span className="sep" />
          <UniBadge name={result.university} />
          {result.year && (<><span className="sep" /><span>{result.year}</span></>)}
        </div>
        <p className="snippet"><Highlight segments={result.snippet} /></p>
        {result.contributions.length > 0 && (
          <div className="terms">
            {result.contributions.map((c) => <span key={c.term} className="term">{c.term} <b>{c.value.toFixed(model === "bm25" ? 2 : 3)}</b></span>)}
          </div>
        )}
      </div>
      <div className="score">
        <ScoreRing value={result.score} ratio={result.score_ratio} model={model} />
        <span className="label">{t(`model.${model}`)}</span>
      </div>
      <style>{`
        .card{display:grid;grid-template-columns:56px 1fr 116px;gap:18px;align-items:start;padding:22px 24px;border-radius:var(--card-radius);background:var(--surface);border:var(--border-w) solid var(--line);box-shadow:var(--card-shadow);backdrop-filter:var(--blur);transition:transform .25s var(--ease-out),border-color .25s,box-shadow .25s;animation:fadeUp .6s var(--ease-out) both;cursor:pointer}
        .card:hover{transform:translateY(-3px);border-color:var(--line-strong);box-shadow:var(--card-shadow-hover)}
        [data-theme="faso"] .card{border-color:var(--ink)}
        [data-theme="faso"] .card:hover{transform:translate(-2px,-2px)}
        .rank{font:800 32px/1 var(--font-display);color:var(--ink-3)}
        .title{font:700 19px/1.3 var(--font-display);letter-spacing:-.01em}
        .byline{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-top:10px;font-size:13.5px;color:var(--ink-2)}
        .sep{width:3px;height:3px;border-radius:50%;background:var(--ink-3)}
        .snippet{margin-top:12px;font-size:15px;line-height:1.65;color:var(--ink-2)}
        .terms{display:flex;gap:6px;margin-top:12px;flex-wrap:wrap}
        .term{font:500 12px var(--font-mono);padding:4px 9px;border-radius:999px;border:1px solid var(--line);color:var(--ink-2)}
        .term b{color:var(--ink)}
        .score{display:flex;flex-direction:column;align-items:center;gap:6px}
        @media (max-width:760px){.card{grid-template-columns:1fr;}.rank{font-size:22px}.score{flex-direction:row}}
      `}</style>
    </article>
  );
}
