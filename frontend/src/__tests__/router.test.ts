import { describe, expect, it } from "vitest";
import { hrefFor, parseHash } from "../router";

describe("parseHash", () => {
  it("lit les pages existantes et les paramètres", () => {
    const r = parseHash("#/search?q=malware&model=bm25");
    expect(r.page).toBe("search");
    expect(r.params.get("model")).toBe("bm25");
    expect(parseHash("").page).toBe("home");
    expect(parseHash("#/inconnu").page).toBe("home");
  });
  it("lit la page auteur et son identifiant", () => {
    const r = parseHash("#/author/oumarou-sie?doc=Document_05");
    expect(r.page).toBe("author");
    expect(r.params.get("id")).toBe("oumarou-sie");
    expect(r.params.get("doc")).toBe("Document_05");
    expect(parseHash("#/author/%C3%A9").params.get("id")).toBe("é");
    expect(parseHash("#/author").page).toBe("home");
    expect(parseHash("#/authors?q=oued").page).toBe("authors");
  });
});

describe("hrefFor", () => {
  it("construit les adresses", () => {
    expect(hrefFor("home")).toBe("#/");
    expect(hrefFor("authors", { q: "ouédraogo" })).toBe("#/authors?q=ou%C3%A9draogo");
    expect(hrefFor("author", { id: "oumarou-sie" })).toBe("#/author/oumarou-sie");
    expect(hrefFor("author", { id: "oumarou-sie", doc: "Document_05", q: undefined })).toBe("#/author/oumarou-sie?doc=Document_05");
    expect(hrefFor("search", { q: "x", lang: "" })).toBe("#/search?q=x");
  });
  it("fait l'aller-retour avec parseHash", () => {
    const r = parseHash(hrefFor("author", { id: "tounwendyam-frederic-ouedraogo", doc: "Document_01" }));
    expect([r.page, r.params.get("id"), r.params.get("doc")]).toEqual(["author", "tounwendyam-frederic-ouedraogo", "Document_01"]);
  });
});
