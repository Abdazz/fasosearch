import { usePrefs } from "../prefs";

export default function EmptyState({ kind, hint, action, msg }: { kind: string; hint?: string; msg?: string;
  action?: { label: string; onClick: () => void } }) {
  const { t } = usePrefs();
  return (
    <div className="empty panel fade-up" role="status">
      <div className="empty-ico" aria-hidden="true">{kind === "server_down" ? "⚡" : "∅"}</div>
      <p>{t(`empty.${kind}`, { msg: msg ?? "" })}</p>
      {hint && <p className="hint">{hint}</p>}
      {action && <button className="btn btn-primary" onClick={action.onClick}>{action.label}</button>}
      <style>{`
        .empty{margin-top:24px;padding:40px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:12px}
        .empty-ico{font:800 40px var(--font-display);color:var(--ink-3)}
        .empty p{font-size:17px;max-width:52ch}.empty .hint{color:var(--ink-2);font-size:15px}
      `}</style>
    </div>
  );
}
