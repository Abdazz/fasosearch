import type { Lang, ModelId } from "./types";

export function pageRange(page: number, pages: number): (number | "…")[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const set = new Set([1, pages, page - 1, page, page + 1].filter((p) => p >= 1 && p <= pages));
  if (page <= 2) [2, 3].forEach((p) => set.add(p));
  const sorted = [...set].sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push("…");
    out.push(p);
  });
  return out;
}

const KNOWN: Record<string, string> = {
  "universite norbert zongo": "UNZ", "norbert zongo university": "UNZ",
  "universite joseph ki-zerbo": "UJKZ", "joseph ki-zerbo university": "UJKZ", "universite de ouagadougou": "UO",
  "universite nazi boni": "UNB", "nazi boni university": "UNB", "universite polytechnique de bobo-dioulasso": "UPB",
  "universite thomas sankara": "UTS", "thomas sankara university": "UTS",
};
const STOP = new Set(["de", "des", "du", "la", "le", "les", "et", "of", "the", "and", "for", "en", "d", "l"]);

export function uniAbbr(name: string): string {
  const first = (name || "").split(";")[0].trim();
  if (!first) return "?";
  const key = first.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  if (KNOWN[key]) return KNOWN[key];
  return first.split(/[\s-]+/).filter((w) => w && !STOP.has(w.toLowerCase())).map((w) => w[0].toUpperCase()).join("").slice(0, 5);
}

export const fmtScore = (v: number, model: ModelId) => (model === "bm25" ? v.toFixed(2) : v.toFixed(3));

export const modelColor = (m: ModelId) => ({ tfidf: "var(--m-tfidf)", w2v: "var(--m-w2v)", bm25: "var(--m-bm25)" })[m];

export const fmtNum = (v: number, lang: Lang) => v.toLocaleString(lang === "fr" ? "fr-FR" : "en-US");

// 20 colors chosen (greedy farthest-point selection in RGB space, seeded with the
// 8 original brand colors) so that up to ~20 universities never share a color, and
// each stays legible against both the dark (Nuit) and cream (Faso) backgrounds.
const PALETTE = [
  "#8b6cff", "#22d3ee", "#ff6fb1", "#f2a900", "#009e49", "#c1272d", "#6ee7b7", "#fb923c",
  "#75c526", "#2675c5", "#cae250", "#c526c5", "#26c590", "#e25068", "#c57526", "#50e268",
  "#26c526", "#5099e2", "#e250e2", "#c5aa26",
];

// Deterministic color assignment, populated once the full list of universities in
// the corpus/map is known (see Lab.tsx/Corpus.tsx): sorting the unique abbreviations
// before indexing into the palette guarantees no two universities collide as long as
// there are no more of them than PALETTE.length.
let colorAssignment: Record<string, string> = {};

export function uniColorMap(names: string[]): Record<string, string> {
  const unique = [...new Set(names.map((n) => uniAbbr(n)).filter((a) => a && a !== "?"))].sort();
  const map: Record<string, string> = {};
  unique.forEach((abbr, i) => { map[abbr] = PALETTE[i % PALETTE.length]; });
  colorAssignment = map;
  return map;
}

export function uniColor(name: string): string {
  const abbr = uniAbbr(name);
  if (colorAssignment[abbr]) return colorAssignment[abbr];
  // Repli déterministe (par hachage) tant que uniColorMap n'a pas encore été
  // appelée avec la liste complète des universités (ex. UniBadge affiché seul).
  let h = 0;
  for (const c of abbr) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
