import { usePrefs } from "../prefs";
import { hrefFor } from "../router";
import type { AuthorLink } from "../types";

export default function AuthorLinks({ links, fallback }: { links: AuthorLink[]; fallback: string }) {
  const { t } = usePrefs();
  if (links.length === 0) return <>{fallback}</>;
  return (
    <>
      {links.map((l, i) => (
        <span key={l.id}>
          {i > 0 && ", "}
          <a className="author-link" href={hrefFor("author", { id: l.id })} title={t("detail.authorLink", { name: l.name })}>{l.name}</a>
        </span>
      ))}
    </>
  );
}
