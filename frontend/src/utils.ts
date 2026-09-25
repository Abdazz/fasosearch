import type { AuthorPaper, Lang, ModelId, SearchResult } from "./types";

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
  // L'Université de Koudougou a été renommée Université Norbert Zongo en 2017 : même
  // institution, donc même abréviation (et donc même couleur dans la carte/le corpus).
  "universite de koudougou": "UNZ", "university of koudougou": "UNZ",
  "universite joseph ki-zerbo": "UJKZ", "joseph ki-zerbo university": "UJKZ", "universite de ouagadougou": "UO",
  "universite nazi boni": "UNB", "nazi boni university": "UNB", "universite polytechnique de bobo-dioulasso": "UPB",
  "universite thomas sankara": "UTS", "thomas sankara university": "UTS",
  "universite ouaga ii": "UO2",
  "institut de l'environnement et recherches agricoles": "INERA",
  "institut superieur de l'informatique et de gestion": "ISIG",
};
const STOP = new Set(["de", "des", "du", "la", "le", "les", "et", "of", "the", "and", "for", "en", "d", "l"]);

export function uniAbbr(name: string): string {
  const first = (name || "").split(";")[0].trim();
  if (!first) return "?";
  const key = first.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  if (KNOWN[key]) return KNOWN[key];
  const initials = first.split(/[\s-]+/).filter((w) => w && !STOP.has(w.toLowerCase())).map((w) => w[0].toUpperCase()).join("");
  // Un nom sans espaces (ou dont tous les mots sauf un sont des mots vides) ne donnerait
  // qu'une seule lettre d'initiale (ex. "AFRICSanté" -> "A") : on se rabat alors sur ses 4
  // premières lettres, plus lisible et plus distinctif qu'un sigle à une lettre.
  if (initials.length <= 1) return (first.replace(/[^a-zA-Z]/g, "").slice(0, 4) || initials || "?").toUpperCase();
  return initials.slice(0, 5);
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

type T = (key: string, vars?: Record<string, string | number>) => string;

/** Nombre de lettres d'une requête, sans accents, chiffres ni ponctuation (même règle que le serveur). */
export const letterCount = (q: string) => q.normalize("NFD").replace(/[^\p{L}]/gu, "").length;

export function fmtPeriod(years: [number, number] | null, t: T): string {
  if (!years) return "";
  return years[0] === years[1] ? String(years[0]) : t("author.period", { from: years[0], to: years[1] });
}

export const fmtPapers = (n: number, t: T) => (n === 1 ? t("authors.papers.one") : t("authors.papers", { n }));

/** Compte de résultats de la page de recherche, avec accord singulier/pluriel. */
export const fmtResultsCount = (n: number, t: T) => (n === 1 ? t("results.count.one") : t("results.count", { total: n }));

/** Normalise une chaîne pour une comparaison insensible aux accents et à la casse
 *  (ex. filtre texte de la page Corpus : "ouedraogo" doit trouver "Ouédraogo"). */
export const foldText = (s: string) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export const nameInitials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");

/** Article d'une page auteur affiché avec la carte de résultat, sans score. */
export const paperToResult = (p: AuthorPaper, i: number): SearchResult =>
  ({ ...p, rank: i + 1, score: 0, score_ratio: 0, contributions: [] });
