import { useEffect, useState } from "react";
import DocumentPanel from "../components/DocumentPanel";
import EmptyState from "../components/EmptyState";
import ResultCard from "../components/ResultCard";
import UniBadge from "../components/UniBadge";
import { ApiError, api } from "../api";
import { usePrefs } from "../prefs";
import { hrefFor, navigate } from "../router";
import type { AuthorProfile } from "../types";
import { fmtPapers, fmtPeriod, nameInitials, paperToResult } from "../utils";

export function AuthorView({ data, onOpen }: { data: AuthorProfile; onOpen: (docId: string) => void }) {
  const { t } = usePrefs();
  const period = fmtPeriod(data.years, t);
  return (
    <>
      <header className="author-head panel fade-up">
        <span className="avatar avatar-lg" aria-hidden="true">{nameInitials(data.name)}</span>
        <div className="author-id">
          <h1 className="h-display author-name">{data.name}</h1>
          <p className="author-meta">{fmtPapers(data.count, t)}{period && <> · {period}</>}</p>
          {data.variants.length > 0 && <p className="author-variants">{`${t("author.alsoWritten")} ${data.variants.join(", ")}`}</p>}
        </div>
      </header>
      {data.universities.length > 0 && (
        <div className="author-block">
          <h2 className="label">{t("author.universities")}</h2>
          <div className="author-chips">{data.universities.map((u) => <UniBadge key={u} name={u} />)}</div>
        </div>
      )}
      {data.coauthors.length > 0 && (
        <div className="author-block">
          <h2 className="label">{t("author.coauthors")}</h2>
          <div className="author-chips">
            {data.coauthors.map((c) => (
              <a key={c.id} className="coauthor" href={hrefFor("author", { id: c.id })}>{`${c.name} (${c.count})`}</a>
            ))}
          </div>
        </div>
      )}
      <div className="author-block">
        <h2 className="label">{t("author.papers")} ({data.documents.length})</h2>
        <div className="author-list">
          {data.documents.map((p, i) => <ResultCard key={p.id} result={paperToResult(p, i)} index={i} onOpen={onOpen} />)}
        </div>
      </div>
      <style>{`
        .author-head{display:flex;gap:20px;align-items:center;padding:24px 26px;margin-top:18px}
        .avatar{flex:none;border-radius:50%;display:grid;place-items:center;font-family:var(--font-display);font-weight:800;color:var(--on-accent);background:var(--active-bg)}
        .avatar-lg{width:76px;height:76px;font-size:26px}
        .author-name{font-size:clamp(28px,4vw,44px)}
        .author-meta{margin-top:6px;color:var(--ink-2);font-size:15px}
        .author-variants{margin-top:6px;color:var(--ink-3);font-size:13.5px}
        .author-block{margin-top:24px;display:flex;flex-direction:column;gap:10px}
        .author-chips{display:flex;flex-wrap:wrap;gap:8px}
        .coauthor{padding:6px 13px;border-radius:999px;border:var(--border-w) solid var(--line);background:var(--surface);color:var(--ink-2);font-size:13.5px;text-decoration:none}
        .coauthor:hover,.coauthor:focus-visible{color:var(--ink);border-color:var(--line-strong)}
        .author-list{display:flex;flex-direction:column;gap:14px}
        @media (max-width:640px){.author-head{flex-direction:column;align-items:flex-start}}
      `}</style>
    </>
  );
}

export default function Author({ params }: { params: URLSearchParams }) {
  const { t } = usePrefs();
  const id = params.get("id") ?? "";
  const doc = params.get("doc");
  const [data, setData] = useState<AuthorProfile | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null); setError(null);
    api.author(id)
      .then((d) => alive && setData(d))
      .catch((e: ApiError) => alive && setError(e));
    return () => { alive = false; };
  }, [id]);

  const open = (docId?: string) => navigate("author", { id, doc: docId });
  const back = () => (window.history.length > 1 ? window.history.back() : navigate("home"));

  return (
    <section className="author-page">
      <button type="button" className="btn" onClick={back}>← {t("author.back")}</button>
      {!data && !error && <div className="spinner" />}
      {error && (error.status === 404
        ? <EmptyState kind="author_not_found" action={{ label: t("author.home"), onClick: () => navigate("home") }} />
        : <EmptyState kind={error.message === "server_down" ? "server_down" : "error"} msg={error.message} />)}
      {data && <AuthorView data={data} onOpen={(d) => open(d)} />}
      {doc && data && (
        <DocumentPanel id={doc} query="" model="tfidf" lang="auto" onClose={() => open(undefined)} onOpen={(d) => open(d)} />
      )}
      <style>{`.author-page{padding-top:14px}`}</style>
    </section>
  );
}
