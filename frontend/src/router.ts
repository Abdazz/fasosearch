import { useEffect, useState } from "react";

export type Page = "home" | "search" | "compare" | "lab" | "corpus";
const PAGES: Page[] = ["home", "search", "compare", "lab", "corpus"];

function parse(): { page: Page; params: URLSearchParams } {
  const [path, qs = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
  const page = (PAGES.includes(path as Page) ? path : "home") as Page;
  return { page, params: new URLSearchParams(qs) };
}

export function navigate(page: Page, params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== "") qs.set(k, String(v)); });
  const s = qs.toString();
  window.location.hash = `/${page === "home" ? "" : page}${s ? "?" + s : ""}`;
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
