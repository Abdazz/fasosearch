import type { ModelId } from "./types";

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

const PALETTE = ["#8b6cff", "#22d3ee", "#ff6fb1", "#f2a900", "#009e49", "#c1272d", "#6ee7b7", "#fb923c"];
export function uniColor(name: string): string {
  let h = 0;
  for (const c of uniAbbr(name)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
