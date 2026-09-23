import { uniAbbr, uniColor } from "../utils";

export default function UniBadge({ name }: { name: string }) {
  if (!name) return null;
  const all = name.split(";").map((s) => s.trim()).filter(Boolean);
  return (
    <span className="uni" title={all.join(" · ")}>
      <i style={{ background: uniColor(all[0]) }}>{uniAbbr(all[0])}</i>{all[0]}
      {all.length > 1 && <em>+{all.length - 1}</em>}
      <style>{`
        .uni{display:inline-flex;align-items:center;gap:7px;font-weight:600;color:var(--ink);padding:3px 11px 3px 3px;border-radius:999px;background:var(--surface-2);font-size:13px;max-width:100%}
        .uni i{min-width:24px;height:22px;padding:0 5px;border-radius:999px;display:grid;place-items:center;font:700 9px var(--font-mono);font-style:normal;color:#fff}
        .uni em{font-style:normal;color:var(--ink-3);font-weight:500}
      `}</style>
    </span>
  );
}
