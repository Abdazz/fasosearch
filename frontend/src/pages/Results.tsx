import { useEffect, useState } from "react";
import DocumentPanel from "../components/DocumentPanel";
import EmptyState from "../components/EmptyState";
import ModelSwitch from "../components/ModelSwitch";
import Pagination from "../components/Pagination";
import QueryPipeline from "../components/QueryPipeline";
import ResultCard from "../components/ResultCard";
import SearchBar from "../components/SearchBar";
import { ApiError, api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { ModelId, QueryLang, SearchResponse } from "../types";

export default function Results({ params }: { params: URLSearchParams }) {
  const { t } = usePrefs();
  const q = (params.get("q") ?? "").trim();
  const model = (["tfidf", "w2v", "bm25"].includes(params.get("model") ?? "") ? params.get("model") : "tfidf") as ModelId;
  const lang = (["fr", "en"].includes(params.get("lang") ?? "") ? params.get("lang") : "auto") as QueryLang;
  const page = Number(params.get("page") ?? 1) || 1;
  const pp = Number(params.get("pp") ?? 10) || 10;
  const doc = params.get("doc");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Le modèle qui a réellement produit `data` : tant qu'une nouvelle requête est en vol
  // (changement de modèle, page, langue…), on continue d'afficher, sous la bonne étiquette,
  // les derniers résultats reçus, jamais des chiffres d'un modèle sous le nom d'un autre.
  const shown = data?.model ?? model;
  const stale = loading && data !== null;

  const go = (over: Record<string, string | number | undefined>) =>
    navigate("search", { q, model, lang: lang === "auto" ? undefined : lang, page, pp, ...over });

  useEffect(() => {
    if (!q) { navigate("home"); return; }
    let alive = true;
    setLoading(true); setError(null);
    api.search({ query: q, model, lang, page, per_page: pp })
      .then((d) => alive && setData(d))
      .catch((e: ApiError) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [q, model, lang, page, pp]);

  return (
    <section className="results-page">
      <SearchBar initial={q} lang={lang} detected={data ? { language: data.query.language, forced: data.query.forced } : null}
        onSubmit={(nq) => go({ q: nq, page: 1 })} onLangChange={(l) => go({ lang: l === "auto" ? undefined : l, page: 1 })} />
      <div className="controls">
        <ModelSwitch value={model} onChange={(m) => go({ model: m, page: 1 })} />
        <button type="button" className="btn compare-btn" onClick={() => navigate("compare", { q, lang: lang === "auto" ? undefined : lang })}>⇆ {t("compare.cta")}</button>
        {data && (
          <div className="meta">
            <b>{t("results.count", { total: data.total })}</b> · {t("results.time", { ms: data.took_ms })}
            {data.threshold !== null && <> · {t("results.threshold", { t: data.threshold.toFixed(2) })}</>}
          </div>
        )}
      </div>
      {data && <QueryPipeline query={data.query} model={shown} />}
      {loading && !data && <div className="spinner" />}
      {stale && <div className="spinner spinner-inline" aria-hidden="true" />}
      {error && <EmptyState kind={error === "server_down" ? "server_down" : "error"} msg={error} />}
      {data?.message === "no_match" && shown === "w2v" && (
        <EmptyState kind="no_match_w2v" msg={data.threshold?.toFixed(2) ?? ""} hint={t("empty.no_match_w2v.hint")}
          action={{ label: `→ ${t("model.tfidf")}`, onClick: () => go({ model: "tfidf", page: 1 }) }} />
      )}
      {data?.message === "no_match" && shown !== "w2v" && (
        <EmptyState kind="no_match" hint={t("empty.no_match.hint")}
          action={{ label: `→ ${t("model.w2v")}`, onClick: () => go({ model: "w2v", page: 1 }) }} />
      )}
      {data?.message && data.message !== "no_match" && <EmptyState kind={data.message} />}
      <div className={`list ${loading ? "is-loading" : ""}`}>
        {data?.results.map((r, i) => <ResultCard key={`${shown}-${r.id}`} result={r} model={shown} index={i}
          onOpen={(id) => go({ doc: id })} />)}
      </div>
      {data && data.total > 0 && (
        <Pagination page={data.page} pages={data.pages} total={data.total} perPage={data.per_page}
          onPage={(p) => go({ page: p })} onPerPage={(n) => go({ pp: n, page: 1 })} />
      )}
      {doc && (
        <DocumentPanel id={doc} query={q} model={model} lang={lang}
          onClose={() => go({ doc: undefined })} onOpen={(id) => go({ doc: id })} />
      )}
      <style>{`
        .results-page{padding-top:14px}
        .controls{display:flex;align-items:center;gap:14px;margin-top:18px;flex-wrap:wrap}
        .compare-btn{border-style:dashed;border-color:var(--line-strong)}
        .meta{margin-left:auto;font-size:13.5px;color:var(--ink-2)}.meta b{color:var(--ink)}
        .list{margin-top:24px;display:flex;flex-direction:column;gap:14px;transition:opacity .2s}
        .list.is-loading{opacity:.45}
        .spinner-inline{margin:14px auto 0}
      `}</style>
    </section>
  );
}
