import { usePrefs } from "../prefs";
import type { ModelId, QueryInfo } from "../types";

export default function QueryPipeline({ query, model }: { query: QueryInfo; model: ModelId }) {
  const { t } = usePrefs();
  const oov = new Set(query.oov);
  return (
    <div className="pipeline panel fade-up">
      <span className="label">{t("pipeline.query")}</span>
      <div className="pv"><span className="flag">{query.language.toUpperCase()}</span>{query.original}</div>
      {query.translated && (<>
        <span className="label">{t("pipeline.translation")}</span>
        <div className="pv"><span className="flag">EN</span>{query.translated}
          {query.method === "glossary" && <span className="warn">⚠ {t("pipeline.approx")}</span>}</div>
      </>)}
      <span className="label">{t("pipeline.processed")}</span>
      <div className="pv">
        {query.preprocessing.tokens.filter((tk) => tk.removed_by !== "punctuation").map((tk, i) => {
          const removed = tk.removed_by !== null;
          const changed = !removed && tk.term !== tk.normalized;
          const isOov = model === "w2v" && tk.term !== null && oov.has(tk.term);
          return (
            <span key={i} className={`tok ${removed ? "x" : ""} ${isOov ? "oov" : ""}`} style={{ animationDelay: `${i * 0.06}s` }}
              title={removed ? t(`lab.removed.${tk.removed_by}`) : isOov ? t("pipeline.oov") : undefined}>
              {removed ? tk.raw : tk.term}{changed && <small>← {tk.normalized}</small>}
              {isOov && <small>∅</small>}
            </span>
          );
        })}
      </div>
      <style>{`
        .pipeline{margin-top:18px;display:grid;grid-template-columns:auto 1fr;gap:10px 18px;align-items:center;padding:16px 20px}
        .pv{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:15px}
        .flag{font-size:11px;font-weight:700;padding:2px 7px;border-radius:6px;border:1px solid var(--line-strong);margin-right:4px}
        .warn{font-size:12px;color:var(--danger);margin-left:8px}
        .tok{font:500 13.5px var(--font-mono);padding:4px 10px;border-radius:8px;background:var(--chip);color:var(--chip-ink);animation:pop .5s both}
        .tok.x{background:none;color:var(--ink-3);text-decoration:line-through;border:1px dashed var(--line)}
        .tok.oov{background:none;border:1px dashed var(--danger);color:var(--danger)}
        .tok small{opacity:.65;margin-left:6px;font-size:11px}
      `}</style>
    </div>
  );
}
