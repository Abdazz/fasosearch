export type ModelId = "tfidf" | "w2v" | "bm25";
export type Lang = "fr" | "en";
export type QueryLang = "auto" | Lang;

export interface Segment { text: string; hit: boolean }
export interface TokenTrace { raw: string; normalized: string | null; term: string | null; removed_by: "punctuation" | "number" | "stopword" | null }
export interface PreprocessResponse { mode: "lemma" | "stem"; terms: string[]; tokens: TokenTrace[] }

export interface QueryInfo {
  original: string; language: Lang; forced: boolean; translated: string | null;
  method: "neural" | "glossary" | null; english: string;
  preprocessing: PreprocessResponse; terms: string[]; oov: string[];
}
export interface Contribution { term: string; value: number }
export interface SearchResult {
  rank: number; id: string; title: string; authors: string; university: string; year: number | null;
  score: number; score_ratio: number; snippet: Segment[]; contributions: Contribution[];
}
export interface SearchResponse {
  query: QueryInfo; model: ModelId; threshold: number | null; total: number; page: number;
  per_page: number; pages: number; results: SearchResult[];
  message: null | "no_terms" | "no_match" | "all_oov"; took_ms: number;
}
export interface CompareItem { rank: number; id: string; title: string; university: string; score: number }
export interface CompareResponse { query: QueryInfo; models: Record<ModelId, CompareItem[]> }
export interface Neighbor { word: string; similarity: number }
export interface DocumentResponse {
  document: { id: string; title: string; authors: string; university: string; year: number | null; url: string | null; abstract: Segment[] };
  explanation: { model: ModelId; score: number; below_threshold: boolean; threshold: number | null;
                 contributions: Contribution[] } | null;
  neighbors: Record<string, Neighbor[]>;
  similar: { id: string; title: string; university: string; year: number | null; similarity: number }[];
}
export interface Stats { documents: number; universities: number; vocabulary: number; w2v_vocabulary: number; year_min: number | null; year_max: number | null }
export interface CorpusDoc { id: string; title: string; authors: string; university: string; year: number | null }
export interface CorpusResponse { documents: CorpusDoc[]; universities: { name: string; count: number }[]; years: { year: number; count: number }[]; vocabulary_size: number }
export interface MapPoint { id: string; title: string; university: string; year: number | null; x: number; y: number }
export interface NeighborsResponse { word: string; term: string; in_vocabulary: boolean; neighbors: Neighbor[] }
