import { describe, expect, it } from "vitest";
import { fmtScore, pageRange, uniAbbr, uniColorMap } from "../utils";

describe("pageRange", () => {
  it("affiche toutes les pages quand il y en a peu", () => {
    expect(pageRange(1, 3)).toEqual([1, 2, 3]);
  });
  it("insère des ellipses autour de la page courante", () => {
    expect(pageRange(6, 12)).toEqual([1, "…", 5, 6, 7, "…", 12]);
    expect(pageRange(1, 12)).toEqual([1, 2, 3, "…", 12]);
  });
});

describe("uniAbbr", () => {
  it("connaît les grandes universités burkinabè", () => {
    expect(uniAbbr("Université Norbert Zongo")).toBe("UNZ");
    expect(uniAbbr("Université Joseph Ki-Zerbo")).toBe("UJKZ");
    expect(uniAbbr("Université Nazi Boni")).toBe("UNB");
  });
  it("calcule des initiales sinon", () => {
    expect(uniAbbr("Institut de Recherche en Sciences Appliquées")).toBe("IRSA");
    expect(uniAbbr("")).toBe("?");
  });
});

describe("fmtScore", () => {
  it("3 décimales pour les cosinus, 2 pour BM25", () => {
    expect(fmtScore(0.82345, "tfidf")).toBe("0.823");
    expect(fmtScore(7.456, "bm25")).toBe("7.46");
  });
});

describe("uniColorMap", () => {
  it("attribue 15 couleurs distinctes à 15 universités distinctes", () => {
    const words = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Iota",
      "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi"];
    const names = words.map((w) => `Université ${w}`);
    const map = uniColorMap(names);
    expect(Object.keys(map).length).toBe(15);
    expect(new Set(Object.values(map)).size).toBe(15);
  });

  it("attribue les mêmes couleurs à la même université quel que soit l'ordre de la liste fournie", () => {
    // Régression : Lab et Corpus appelaient chacun uniColorMap avec des listes
    // différentes (une seule affiliation par point de carte vs toutes les
    // affiliations séparées), ce qui pouvait faire varier l'ordre de tri et donc
    // la couleur assignée à une même université. Construire la carte à partir de
    // la même liste, dans un ordre différent, doit toujours produire le même
    // résultat.
    const names = ["Université Nazi Boni", "Université Joseph Ki-Zerbo", "University of Koudougou",
      "Université Ouaga II", "Institut de Recherche Pour le Développement"];
    const shuffled = [...names].reverse();
    expect(uniColorMap(shuffled)).toEqual(uniColorMap(names));
  });
});
