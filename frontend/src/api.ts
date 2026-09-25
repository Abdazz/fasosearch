import type { AuthorProfile, AuthorSummary, CompareResponse, CorpusResponse, DocumentResponse, MapPoint, ModelId, NeighborsResponse,
  PreprocessResponse, QueryLang, SearchResponse, Stats } from "./types";

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, { headers: { "content-type": "application/json" }, ...init });
  } catch {
    throw new ApiError("server_down");
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(body.detail ?? `HTTP ${r.status}`, r.status);
  return body as T;
}
const post = <T,>(path: string, data: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(data) });

export const api = {
  search: (b: { query: string; model: ModelId; lang: QueryLang; page: number; per_page: number }) =>
    post<SearchResponse>("/api/search", b),
  compare: (b: { query: string; lang: QueryLang; k?: number }) => post<CompareResponse>("/api/compare", b),
  document: (id: string, query: string, model: ModelId, lang: QueryLang) =>
    call<DocumentResponse>(`/api/documents/${encodeURIComponent(id)}?` + new URLSearchParams({ query, model, lang })),
  preprocess: (text: string, mode: "lemma" | "stem") => post<PreprocessResponse>("/api/preprocess", { text, mode }),
  neighbors: (word: string) => call<NeighborsResponse>("/api/w2v/neighbors?" + new URLSearchParams({ word })),
  stats: () => call<Stats>("/api/stats"),
  corpus: () => call<CorpusResponse>("/api/corpus"),
  map: () => call<{ points: MapPoint[] }>("/api/map"),
  authors: (q: string) => call<AuthorSummary[]>("/api/authors?" + new URLSearchParams({ q })),
  author: (id: string) => call<AuthorProfile>(`/api/authors/${encodeURIComponent(id)}`),
};
