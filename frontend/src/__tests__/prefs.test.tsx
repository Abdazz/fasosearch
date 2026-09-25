import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PrefsProvider, usePrefs } from "../prefs";

function ThemeProbe() {
  const { theme } = usePrefs();
  return <span>{theme}</span>;
}

describe("préférences", () => {
  it("le thème Faso est le thème par défaut", () => {
    expect(renderToStaticMarkup(<PrefsProvider><ThemeProbe /></PrefsProvider>)).toBe("<span>faso</span>");
  });
});
