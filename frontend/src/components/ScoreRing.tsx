import { useId, type CSSProperties } from "react";
import { usePrefs } from "../prefs";
import type { ModelId } from "../types";
import { fmtScore } from "../utils";

export default function ScoreRing({ value, ratio, model, size = 88 }: { value: number; ratio: number; model: ModelId; size?: number }) {
  const { t } = usePrefs();
  const gid = useId();
  const r = size / 2 - 7, c = 2 * Math.PI * r;
  const fill = model === "bm25" ? ratio : Math.max(0, Math.min(1, value));
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <defs><linearGradient id={gid} x1="0" x2="1"><stop offset="0" stopColor="var(--accent)" /><stop offset="1" stopColor="var(--accent-2)" /></linearGradient></defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--ring-track)" strokeWidth="7" />
        <circle className="ring-p" cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`url(#${gid})`} strokeWidth="7"
          strokeLinecap="round" strokeDasharray={c} style={{ strokeDashoffset: c * (1 - fill), "--c": c } as CSSProperties} />
      </svg>
      <div className="ring-v"><div>{fmtScore(value, model)}<small>{model === "bm25" ? t("score.bm25") : t("score.cosine")}</small></div></div>
      <style>{`
        .ring{position:relative;flex:none}.ring svg{transform:rotate(-90deg)}
        .ring-p{animation:ringFill 1.2s var(--ease-out) both}
        @keyframes ringFill{from{stroke-dashoffset:var(--c)}}
        .ring-v{position:absolute;inset:0;display:grid;place-items:center;font:700 16px var(--font-mono)}
        .ring-v small{display:block;text-align:center;font:600 8.5px var(--font-body);letter-spacing:.1em;color:var(--ink-3);margin-top:1px}
      `}</style>
    </div>
  );
}
