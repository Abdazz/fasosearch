import { useEffect, useState } from "react";
import AuthorCard from "../components/AuthorCard";
import EmptyState from "../components/EmptyState";
import SearchBar from "../components/SearchBar";
import { ApiError, api } from "../api";
import { usePrefs } from "../prefs";
import { navigate } from "../router";
import type { AuthorSummary } from "../types";
import { letterCount } from "../utils";

export function AuthorList({ authors, q }: { authors: AuthorSummary[]; q: string }) {
  const { t } = usePrefs();
  if (authors.length === 0) {
    return <EmptyState kind="authors_none" msg={q}
      action={{ label: t("authors.searchPapers", { q }), onClick: () => navigate("search", { q }) }} />;
  }
  return (
    <>
      <div className="authors-meta">
        <b>{authors.length === 1 ? t("authors.count.one") : t("authors.count", { n: authors.length })}</b>
      </div>
      <div className="author-grid">{authors.map((a, i) => <AuthorCard key={a.id} author={a} index={i} />)}</div>
      <style>{`
        .authors-meta{margin-top:18px;font-size:13.5px;color:var(--ink-2)}
        .author-grid{margin-top:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
        @media (max-width:760px){.author-grid{grid-template-columns:1fr}}
      `}</style>
    </>
  );
}

export default function Authors({ params }: { params: URLSearchParams }) {
  const q = (params.get("q") ?? "").trim();
  const short = letterCount(q) < 2;
  const [data, setData] = useState<AuthorSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q) { navigate("home"); return; }
    if (short) return;
    let alive = true;
    setData(null); setError(null);
    api.authors(q)
      .then((d) => alive && setData(d))
      .catch((e: ApiError) => alive && setError(e.message));
    return () => { alive = false; };
  }, [q, short]);

  return (
    <section className="authors-page">
      <SearchBar initial={q} lang="auto" mode="authors" onLangChange={() => {}}
        onModeChange={(m) => m === "papers" && navigate("search", { q })}
        onSubmit={(nq) => navigate("authors", { q: nq })} />
      {short && <EmptyState kind="authors_short" />}
      {!short && !data && !error && <div className="spinner" />}
      {!short && error && <EmptyState kind={error === "server_down" ? "server_down" : "error"} msg={error} />}
      {!short && data && <AuthorList authors={data} q={q} />}
      <style>{`.authors-page{padding-top:14px}`}</style>
    </section>
  );
}
