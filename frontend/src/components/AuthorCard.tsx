import { usePrefs } from "../prefs";
import { hrefFor } from "../router";
import type { AuthorSummary } from "../types";
import { fmtPapers, fmtPeriod, nameInitials } from "../utils";
import Highlight from "./Highlight";
import UniBadge from "./UniBadge";

export default function AuthorCard({ author, index }: { author: AuthorSummary; index: number }) {
  const { t } = usePrefs();
  const unis = author.universities;
  const period = fmtPeriod(author.years, t);
  return (
    <a className="acard" href={hrefFor("author", { id: author.id })} style={{ animationDelay: `${index * 0.05}s` }}>
      <span className="avatar" aria-hidden="true">{nameInitials(author.name)}</span>
      <span className="acard-body">
        <b className="acard-name"><Highlight segments={author.segments} /></b>
        <span className="acard-meta">{fmtPapers(author.count, t)}{period && <> · {period}</>}</span>
        {unis.length > 0 && (
          <span className="acard-unis">
            {unis.slice(0, 3).map((u) => <UniBadge key={u} name={u} />)}
            {unis.length > 3 && <em>+{unis.length - 3}</em>}
          </span>
        )}
      </span>
      <style>{`
        .acard{display:flex;gap:16px;align-items:flex-start;padding:18px 20px;border-radius:var(--card-radius);background:var(--surface);border:var(--border-w) solid var(--line);box-shadow:var(--card-shadow);backdrop-filter:var(--blur);color:inherit;text-decoration:none;transition:transform .25s var(--ease-out),border-color .25s,box-shadow .25s;animation:fadeUp .6s var(--ease-out) both}
        .acard:hover,.acard:focus-visible{transform:translateY(-3px);border-color:var(--line-strong);box-shadow:var(--card-shadow-hover)}
        [data-theme="faso"] .acard{border-color:var(--ink)}
        .avatar{flex:none;width:48px;height:48px;border-radius:50%;display:grid;place-items:center;font:800 16px var(--font-display);color:var(--on-accent);background:var(--active-bg)}
        .acard-body{display:flex;flex-direction:column;gap:6px;min-width:0}
        .acard-name{font:700 18px/1.3 var(--font-display)}
        .acard-meta{font-size:13.5px;color:var(--ink-2)}
        .acard-unis{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
        .acard-unis em{font-style:normal;color:var(--ink-3);font-size:13px}
      `}</style>
    </a>
  );
}
