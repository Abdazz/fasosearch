import { useEffect, useRef } from "react";
import { usePrefs } from "../prefs";

/** Décor de fond : constellation animée (Nuit) ou bandeau Faso Dan Fani + halo (Faso). */
export default function Backdrop() {
  const { theme } = usePrefs();
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (theme !== "nuit") return;
    const cv = ref.current!;
    const ctx = cv.getContext("2d")!;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const pts = Array.from({ length: 46 }, () => ({ x: Math.random(), y: Math.random(),
      vx: (Math.random() - .5) * .00025, vy: (Math.random() - .5) * .00025 }));
    const draw = () => {
      const w = (cv.width = window.innerWidth), h = (cv.height = window.innerHeight);
      ctx.clearRect(0, 0, w, h);
      for (const p of pts) {
        if (!reduce) { p.x = (p.x + p.vx + 1) % 1; p.y = (p.y + p.vy + 1) % 1; }
      }
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const dx = (pts[i].x - pts[j].x) * w, dy = (pts[i].y - pts[j].y) * h, d = Math.hypot(dx, dy);
        if (d < 150) {
          ctx.strokeStyle = `rgba(139,108,255,${.22 * (1 - d / 150)})`;
          ctx.beginPath(); ctx.moveTo(pts[i].x * w, pts[i].y * h); ctx.lineTo(pts[j].x * w, pts[j].y * h); ctx.stroke();
        }
      }
      ctx.fillStyle = "rgba(185,168,255,.7)";
      for (const p of pts) { ctx.beginPath(); ctx.arc(p.x * w, p.y * h, 1.6, 0, Math.PI * 2); ctx.fill(); }
      if (!reduce) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [theme]);

  return (
    <>
      {theme === "faso" && <div className="fdf" aria-hidden />}
      <div className={`backdrop backdrop-${theme}`} aria-hidden>
        {theme === "nuit" && <canvas ref={ref} />}
      </div>
      <style>{`
        .fdf{position:relative;z-index:2;height:10px;background:repeating-linear-gradient(90deg,#c1272d 0 26px,#009e49 26px 52px,#f2a900 52px 60px,#231710 60px 66px,#fbf6ec 66px 70px,#231710 70px 76px)}
        .backdrop{position:fixed;inset:0;pointer-events:none;z-index:0}
        .backdrop canvas{width:100%;height:100%;opacity:.55}
        .backdrop-nuit{background:radial-gradient(900px 500px at 12% -5%,rgba(139,108,255,.28),transparent 60%),radial-gradient(700px 500px at 100% 30%,rgba(34,211,238,.14),transparent 60%),radial-gradient(600px 400px at 40% 110%,rgba(255,111,177,.10),transparent 60%)}
        .backdrop-faso{background:radial-gradient(700px 420px at 95% 0%,rgba(242,169,0,.16),transparent 60%),radial-gradient(600px 400px at 0% 100%,rgba(0,158,73,.07),transparent 60%)}
      `}</style>
    </>
  );
}
