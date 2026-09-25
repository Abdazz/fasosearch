import { describe, expect, it } from "vitest";
import { fmtPapers, fmtPeriod, fmtResultsCount, fmtScore, foldText, letterCount, nameInitials, pageRange, paperToResult, uniAbbr, uniColorMap } from "../utils";
import { translate } from "../i18n";

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

  it("connaît les renommages et cas particuliers du corpus réel (M1)", () => {
    // L'Université de Koudougou a été renommée Université Norbert Zongo en 2017 : même
    // institution, donc même abréviation (et donc même couleur) que "Université Norbert Zongo".
    expect(uniAbbr("University of Koudougou")).toBe("UNZ");
    expect(uniAbbr("Université de Koudougou")).toBe("UNZ");
    expect(uniAbbr("Institut de l'Environnement et Recherches Agricoles")).toBe("INERA");
    expect(uniAbbr("Institut Supérieur de l'Informatique et de Gestion")).toBe("ISIG");
    expect(uniAbbr("Université Ouaga II")).toBe("UO2");
    // Nom sans espaces : les initiales calculées ("A") ne feraient qu'une seule lettre ->
    // repli sur les 4 premières lettres du nom.
    expect(uniAbbr("AFRICSanté")).toBe("AFRI");
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

const tFr = (k: string, v?: Record<string, string | number>) => translate("fr", k, v);
const tEn = (k: string, v?: Record<string, string | number>) => translate("en", k, v);

describe("auteurs", () => {
  it("compte les lettres sans accents ni ponctuation", () => {
    expect(letterCount("é")).toBe(1);
    expect(letterCount(" - ")).toBe(0);
    expect(letterCount("Ou")).toBe(2);
  });
  it("formate la période", () => {
    expect(fmtPeriod([2012, 2024], tFr)).toBe("2012 à 2024");
    expect(fmtPeriod([2012, 2024], tEn)).toBe("2012 to 2024");
    expect(fmtPeriod([2020, 2020], tFr)).toBe("2020");
    expect(fmtPeriod(null, tFr)).toBe("");
  });
  it("accorde le nombre d'articles", () => {
    expect(fmtPapers(1, tFr)).toBe("1 article");
    expect(fmtPapers(27, tFr)).toBe("27 articles");
    expect(fmtPapers(1, tEn)).toBe("1 paper");
  });
  it("calcule les initiales", () => {
    expect(nameInitials("Tounwendyam Frédéric Ouédraogo")).toBe("TF");
    expect(nameInitials("Zongo")).toBe("Z");
  });
  it("transforme un article d'auteur en carte sans score", () => {
    const r = paperToResult({ id: "D1", title: "T", authors: "A", university: "U", year: 2020, snippet: [] }, 2);
    expect(r.rank).toBe(3);
    expect(r.contributions).toEqual([]);
  });
});

describe("foldText", () => {
  it("retire les accents et met en minuscules", () => {
    expect(foldText("Ouédraogo")).toBe("ouedraogo");
    expect(foldText("OUEDRAOGO")).toBe("ouedraogo");
    expect(foldText("ouedraogo")).toBe("ouedraogo");
  });
  it("gère les chaînes vides ou sans accent", () => {
    expect(foldText("")).toBe("");
    expect(foldText("Zongo")).toBe("zongo");
  });
});

describe("fmtResultsCount", () => {
  it("accorde le singulier quand le total vaut 1", () => {
    expect(fmtResultsCount(1, tFr)).toBe("1 document pertinent");
    expect(fmtResultsCount(1, tEn)).toBe("1 relevant document");
  });
  it("garde le pluriel sinon", () => {
    expect(fmtResultsCount(23, tFr)).toBe("23 documents pertinents");
    expect(fmtResultsCount(0, tEn)).toBe("0 relevant documents");
  });
});
