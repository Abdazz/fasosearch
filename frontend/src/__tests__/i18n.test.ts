import { describe, expect, it } from "vitest";
import { DICT, translate } from "../i18n";

describe("i18n", () => {
  it("FR et EN ont exactement les mêmes clés", () => {
    expect(Object.keys(DICT.en).sort()).toEqual(Object.keys(DICT.fr).sort());
  });
  it("remplace les variables", () => {
    expect(translate("fr", "results.range", { from: 1, to: 10, total: 23 })).toBe("Résultats 1 à 10 sur 23");
  });
  it("ne contient jamais de tiret cadratin ni demi-cadratin", () => {
    const dashes = /[\u2014\u2013]/;
    for (const dict of [DICT.fr, DICT.en]) {
      for (const [key, value] of Object.entries(dict)) {
        expect(dashes.test(value), `${key} contient un tiret interdit: "${value}"`).toBe(false);
      }
    }
  });
});
