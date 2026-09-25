import { useEffect, useState } from "react";

export type Page = "home" | "search" | "compare" | "lab" | "corpus" | "authors" | "author";
const PAGES: Page[] = ["home", "search", "compare", "lab", "corpus", "authors", "author"];
type Params = Record<string, string | number | undefined>;

export function parseHash(hash: string): { page: Page; params: URLSearchParams } {
  const [path, qs = ""] = hash.replace(/^#\/?/, "").split("?");
  const [head, ...rest] = path.split("/");
  const params = new URLSearchParams(qs);
  let page = (PAGES.includes(head as Page) ? head : "home") as Page;
  if (page === "author") {
    let id = "";
    try { id = decodeURIComponent(rest.join("/")); } catch { id = ""; }
    if (id) params.set("id", id);
    else page = "home";
  }
  return { page, params };
}

function parse() {
  return parseHash(window.location.hash);
}

export function hrefFor(page: Page, params: Params = {}): string {
  const { id, ...others } = params;
  const qs = new URLSearchParams();
  Object.entries(page === "author" ? others : params).forEach(([k, v]) => { if (v !== undefined && v !== "") qs.set(k, String(v)); });
  const s = qs.toString();
  const path = page === "home" ? "" : page === "author" ? `author/${encodeURIComponent(String(id ?? ""))}` : page;
  return `#/${path}${s ? "?" + s : ""}`;
}

export function navigate(page: Page, params: Params = {}) {
  window.location.hash = hrefFor(page, params);
}

export function useRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo({ top: 0 }); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
