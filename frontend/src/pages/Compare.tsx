import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import SearchBar from "../components/SearchBar";
import UniBadge from "../components/UniBadge";
import { ApiError, api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { CompareResponse, ModelId, QueryLang } from "../types";
import { fmtScore } from "../utils";

const MODELS: ModelId[] = ["tfidf", "w2v", "bm25"];

export default function Compare({ params }: { params: URLSearchParams }) {
  const { t } = usePrefs();
  const q = params.get("q") ?? "";
  const lang = (["fr", "en"].includes(params.get("lang") ?? "") ? params.get("lang") : "auto") as QueryLang;
  const [data, setData] = useState<CompareResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    if (!q) { setData(null); setErr(null); return; }
    let alive = true;
    setLoading(true); setErr(null);
    api.compare({ query: q, lang, k: 10 })
      .then((d) => { if (alive) setData(d); })
      .catch((e: ApiError) => { if (alive) setErr(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [q, lang]);

  const open = (m: ModelId, id: string) => navigate("search", { q, model: m, lang: lang === "auto" ? undefined : lang, doc: id });

  const tfidfRank = new Map<string, number>(data?.models.tfidf.map((r) => [r.id, r.rank] as [string, number]));
  const tops = data ? MODELS.map((m) => data.models[m][0]?.id).filter(Boolean) : [];
  const agreement = tops.length ? Math.max(...tops.map((id) => tops.filter((x) => x === id).length)) : 0;

  return (
    <section className="cmp">
      <h1 className="h-display cmp-h">{t("compare.title")}</h1>
      <p className="cmp-sub">{t("compare.subtitle")}</p>
      <SearchBar initial={q} lang={lang} detected={data ? { language: data.query.language, forced: data.query.forced } : null}
        onSubmit={(nq) => navigate("compare", { q: nq, lang: lang === "auto" ? undefined : lang })}
        onLangChange={(l) => navigate("compare", { q, lang: l === "auto" ? undefined : l })} />
      {!q && (
        <div className="cmp-hint panel fade-up" role="note">
          <p>{t("compare.placeholder")}</p>
        </div>
      )}
      {err && <EmptyState kind={err === "server_down" ? "server_down" : "error"} msg={err} />}
      {loading && !data && <div className="spinner" />}
      {data && (<>
        <div className="cmp-agree label">{t("compare.agreement", { n: agreement })}</div>
        <div className={`cmp-grid ${loading ? "is-loading" : ""}`}>
          {MODELS.map((m, ci) => (
            <div key={m} className="cmp-col panel fade-up" style={{ animationDelay: `${ci * 0.08}s` }}>
              <div className="cmp-colh">
                <span className="dot" style={{ background: `var(--m-${m})` }} /><b>{t(`model.${m}`)}</b>
                <small>{t(`model.${m}.desc`)}</small>
              </div>
              {data.models[m].length === 0 && <p className="cmp-empty">{t("compare.empty")}</p>}
              {data.models[m].map((r) => {
                const base = tfidfRank.get(r.id);
                const delta = m === "tfidf" ? null : base === undefined ? "new" : base - r.rank;
                const active = hover === r.id;
                return (
                  <div key={r.id} className={`cmp-row ${active ? "hl" : ""} ${hover && !active ? "dim" : ""}`}
                    role="button" tabIndex={0}
                    onMouseEnter={() => setHover(r.id)} onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(r.id)} onBlur={() => setHover(null)}
                    onClick={() => open(m, r.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") open(m, r.id);
                      else if (e.key === " ") { e.preventDefault(); open(m, r.id); }
                    }}>
                    <span className="cmp-rank">{r.rank}</span>
                    <span className="cmp-title">
                      {r.title}
                      <UniBadge name={r.university} />
                    </span>
                    <span className="cmp-score">
                      {fmtScore(r.score, m)}
                      {delta === "new" && <em className="up">{t("compare.new")}</em>}
                      {typeof delta === "number" && delta !== 0 && (
                        <em className={delta > 0 ? "up" : "down"}>{delta > 0 ? `↑${delta}` : `↓${-delta}`}</em>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </>)}
      <style>{`
        .cmp{padding-top:22px;display:flex;flex-direction:column;gap:16px}
        .cmp-h{font-size:clamp(32px,4.5vw,52px)}.cmp-sub{color:var(--ink-2);font-size:16px}
        .cmp-agree{margin-top:6px}
        .cmp-hint{margin-top:24px;padding:32px;text-align:center;color:var(--ink-2);font-size:16px}
        .cmp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;transition:opacity .2s}
        .cmp-grid.is-loading{opacity:.55}
        .cmp-col{padding:16px;display:flex;flex-direction:column;gap:6px;box-shadow:var(--card-shadow)}
        .cmp-colh{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;font-family:var(--font-display);font-size:17px}
        .cmp-colh small{width:100%;font:400 12.5px var(--font-body);color:var(--ink-3)}
        .cmp-empty{color:var(--ink-3);font-size:14px}
        .cmp-row{display:grid;grid-template-columns:26px 1fr auto;gap:10px;align-items:center;padding:9px 10px;border-radius:12px;cursor:pointer;transition:background .2s,opacity .2s}
        .cmp-row:hover,.cmp-row.hl{background:var(--mark)}
        .cmp-row.dim{opacity:.4}
        .cmp-rank{font:800 16px var(--font-display);color:var(--ink-3)}
        .cmp-title{font-size:13.5px;font-weight:600;line-height:1.35;display:flex;flex-direction:column;align-items:flex-start;gap:4px;min-width:0}
        .cmp-title .uni{font-size:11px;padding:2px 8px 2px 2px}
        .cmp-title .uni i{min-width:18px;height:16px;font-size:8px}
        .cmp-score{font:600 12.5px var(--font-mono);display:flex;flex-direction:column;align-items:flex-end;gap:2px}
        .cmp-score em{font-style:normal;font-size:11px;font-weight:700}
        .up{color:var(--accent-2)}.down{color:var(--danger)}
        .dot{width:9px;height:9px;border-radius:50%;flex:none}
        @media (max-width:900px){.cmp-grid{grid-template-columns:1fr}}
      `}</style>
    </section>
  );
}
