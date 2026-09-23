import { useLayoutEffect, useRef, useState } from "react";
import { usePrefs } from "../prefs";
import type { ModelId } from "../types";

const MODELS: ModelId[] = ["tfidf", "w2v", "bm25"];

export default function ModelSwitch({ value, onChange }: { value: ModelId; onChange: (m: ModelId) => void }) {
  const { t } = usePrefs();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [pill, setPill] = useState({ left: 0, width: 0 });
  useLayoutEffect(() => {
    const b = refs.current[value];
    if (b) setPill({ left: b.offsetLeft, width: b.offsetWidth });
  }, [value, t]);
  return (
    <div className="seg" role="radiogroup">
      <div className="seg-pill" style={pill} />
      {MODELS.map((m) => (
        <button key={m} ref={(el) => (refs.current[m] = el)} type="button" role="radio" aria-checked={value === m}
          className={value === m ? "on" : ""} onClick={() => onChange(m)} title={t(`model.${m}.desc`)}>
          <span className="dot" style={{ background: `var(--m-${m})` }} />{t(`model.${m}`)}
        </button>
      ))}
      <style>{`
        .seg{position:relative;display:inline-flex;padding:4px;border-radius:999px;background:var(--surface);border:var(--border-w) solid var(--line)}
        .seg button{position:relative;z-index:1;border:0;background:none;color:var(--ink-2);font:600 14px var(--font-body);padding:9px 18px;border-radius:999px;display:flex;align-items:center;gap:8px;transition:color .3s}
        .seg button.on{color:var(--on-accent)}
        .seg-pill{position:absolute;z-index:0;top:4px;bottom:4px;border-radius:999px;background:var(--active-bg);transition:left .4s var(--ease-spring),width .4s var(--ease-spring)}
        .dot{width:8px;height:8px;border-radius:50%}
      `}</style>
    </div>
  );
}
