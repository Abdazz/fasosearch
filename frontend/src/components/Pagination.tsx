import { usePrefs } from "../prefs";
import { pageRange } from "../utils";

export default function Pagination({ page, pages, total, perPage, onPage, onPerPage }: {
  page: number; pages: number; total: number; perPage: number; onPage: (p: number) => void; onPerPage: (n: number) => void }) {
  const { t } = usePrefs();
  const from = total ? (page - 1) * perPage + 1 : 0, to = Math.min(total, page * perPage);
  return (
    <div className="pager">
      <div className="info">{t("results.range", { from, to, total })}</div>
      <div className="pages">
        <button type="button" className="pg" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label={t("pagination.prev")}>←</button>
        {pageRange(page, pages).map((p, i) => p === "…"
          ? <span key={`e${i}`} className="pg ghost">…</span>
          : <button key={p} type="button" className={`pg ${p === page ? "on" : ""}`} aria-current={p === page} onClick={() => onPage(p)}>{p}</button>)}
        <button type="button" className="pg" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label={t("pagination.next")}>→</button>
      </div>
      <label className="pp">{t("results.perPage")}
        <select value={perPage} onChange={(e) => onPerPage(Number(e.target.value))}>
          {[10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
      <style>{`
        .pager{margin-top:30px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
        .pager .info{font-size:14px;color:var(--ink-2)}
        .pages{display:flex;align-items:center;gap:6px}
        .pg{min-width:42px;height:42px;padding:0 12px;border-radius:12px;border:var(--border-w) solid var(--line);background:var(--surface);font:600 14px var(--font-mono);display:grid;place-items:center}
        [data-theme="faso"] .pg{border-color:var(--ink)}
        .pg:hover:not(:disabled){border-color:var(--line-strong)}
        .pg:disabled{opacity:.35;cursor:default}
        .pg.on{background:var(--active-bg);border-color:transparent;color:var(--on-accent)}
        .pg.ghost{border:0;background:none;color:var(--ink-3)}
        .pp{display:flex;align-items:center;gap:8px;font-size:13.5px;color:var(--ink-2)}
        .pp select{background:var(--surface-solid);color:var(--ink);border:var(--border-w) solid var(--line);border-radius:10px;padding:8px 10px;font:600 13px var(--font-body)}
      `}</style>
    </div>
  );
}
