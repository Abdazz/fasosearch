import { describe, expect, it } from "vitest";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import AuthorCard from "../components/AuthorCard";
import AuthorLinks from "../components/AuthorLinks";
import ResultCard from "../components/ResultCard";
import SearchBar from "../components/SearchBar";
import { AuthorList } from "../pages/Authors";
import { AuthorView } from "../pages/Author";
import { PrefsProvider } from "../prefs";
import type { AuthorProfile, AuthorSummary } from "../types";

const html = (el: ReactElement) => renderToStaticMarkup(<PrefsProvider>{el}</PrefsProvider>);
const noop = () => {};

const SIE: AuthorSummary = {
  id: "oumarou-sie", name: "Oumarou Sié", count: 16, universities: ["Université Joseph Ki-Zerbo"], years: [2010, 2024],
  segments: [{ text: "Oumarou", hit: true }, { text: " Sié", hit: false }],
};

describe("SearchBar", () => {
  it("affiche la bascule et masque la langue en mode Auteurs", () => {
    const out = html(<SearchBar lang="auto" mode="authors" onModeChange={noop} onSubmit={noop} onLangChange={noop} />);
    expect(out).toContain('aria-pressed="true">Auteurs');
    expect(out).toContain('aria-pressed="false">Articles');
    expect(out).not.toContain('class="detect"');
    expect(out).toContain("Nom d&#x27;un auteur");
  });
  it("reste identique sans bascule en mode Articles", () => {
    const out = html(<SearchBar lang="auto" onSubmit={noop} onLangChange={noop} />);
    expect(out).not.toContain("aria-pressed");
    expect(out).toContain('class="detect"');
  });
});

describe("AuthorCard", () => {
  it("renvoie vers la page de l'auteur avec le nom surligné", () => {
    const out = html(<AuthorCard author={SIE} index={0} />);
    expect(out).toContain('href="#/author/oumarou-sie"');
    expect(out).toContain("<mark>Oumarou</mark>");
    expect(out).toContain("16 articles");
    expect(out).toContain("2010 à 2024");
  });
});

describe("AuthorList", () => {
  it("affiche le nombre d'auteurs", () => {
    expect(html(<AuthorList authors={[SIE]} q="oum" />)).toContain("1 auteur trouvé");
  });
  it("propose la recherche d'articles quand rien ne correspond", () => {
    const out = html(<AuthorList authors={[]} q="zzz" />);
    expect(out).toContain("Aucun auteur ne correspond à « zzz »");
    expect(out).toContain("Chercher « zzz » dans les articles");
  });
});

const PROFILE: AuthorProfile = {
  id: "tounwendyam-frederic-ouedraogo", name: "Tounwendyam Frédéric Ouédraogo", count: 2,
  universities: ["Université Norbert Zongo"], years: [2019, 2024],
  variants: ["Frédéric Ouédraogo", "Frédéric T. Ouédraogo"],
  coauthors: [{ id: "oumarou-sie", name: "Oumarou Sié", count: 2 }],
  documents: [
    { id: "Document_40", title: "Titre récent", authors: "A; B", university: "Université Norbert Zongo", year: 2024, snippet: [{ text: "Extrait.", hit: false }] },
    { id: "Document_12", title: "Titre ancien", authors: "A", university: "Université Norbert Zongo", year: 2019, snippet: [] },
  ],
};

describe("AuthorView", () => {
  it("affiche le profil enrichi et les articles sans score", () => {
    const out = html(<AuthorView data={PROFILE} onOpen={noop} />);
    expect(out).toContain("Tounwendyam Frédéric Ouédraogo");
    expect(out).toContain("2 articles");
    expect(out).toContain("2019 à 2024");
    expect(out).toContain("Aussi écrit : Frédéric Ouédraogo, Frédéric T. Ouédraogo");
    expect(out).toContain("Universités de ses articles");
    expect(out).toContain('href="#/author/oumarou-sie"');
    expect(out).toContain("Oumarou Sié (2)");
    expect(out.indexOf("Titre récent")).toBeLessThan(out.indexOf("Titre ancien"));
    expect(out).not.toContain('class="score"');
  });
});

describe("ResultCard", () => {
  it("garde la colonne score quand un modèle est fourni", () => {
    const r = { rank: 1, id: "D", title: "T", authors: "A", university: "", year: null, score: 0.5, score_ratio: 1, snippet: [], contributions: [] };
    expect(html(<ResultCard result={r} model="tfidf" index={0} onOpen={noop} />)).toContain('class="score"');
  });
});

describe("AuthorLinks", () => {
  it("rend chaque auteur cliquable", () => {
    const out = html(<AuthorLinks links={[{ id: "a-b", name: "A. B" }, { id: "c-d", name: "C. D" }]} fallback="A. B; C. D" />);
    expect(out).toContain('href="#/author/a-b"');
    expect(out).toContain('href="#/author/c-d"');
    expect(out).toContain("Voir tous les articles de C. D");
  });
  it("retombe sur le texte brut sans liens", () => {
    expect(html(<AuthorLinks links={[]} fallback="X Y" />)).toBe("X Y");
  });
});
