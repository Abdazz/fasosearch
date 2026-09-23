import { describe, expect, it } from "vitest";
import { DICT, translate } from "../i18n";

describe("i18n", () => {
  it("FR et EN ont exactement les mêmes clés", () => {
    expect(Object.keys(DICT.en).sort()).toEqual(Object.keys(DICT.fr).sort());
  });
  it("remplace les variables", () => {
    expect(translate("fr", "results.range", { from: 1, to: 10, total: 23 })).toBe("Résultats 1 – 10 sur 23");
  });
});
