import { describe, expect, it } from "vitest";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import AuthorCard from "../components/AuthorCard";
import SearchBar from "../components/SearchBar";
import { AuthorList } from "../pages/Authors";
import { PrefsProvider } from "../prefs";
import type { AuthorSummary } from "../types";

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
