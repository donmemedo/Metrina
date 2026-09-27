"use client";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useApp } from "./shell";

export const COLORS: Record<string, string> = {
  google: "var(--blue)", telegram: "var(--cyan)", instagram: "var(--pink)", x: "var(--gray)", direct: "var(--green)",
  internal: "var(--orange)", politics: "var(--indigo)", economy: "var(--orange)", tech: "var(--blue)",
  sport: "var(--green)", culture: "var(--pink)", health: "var(--teal)", mobile: "var(--blue)",
  desktop: "var(--purple)", tablet: "var(--orange)",
};

/** Eased count toward `target`; starts from 0 so first paint counts up. */
export function useTween(target: number, ms = 900) {
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const start = performance.now(), a = from.current;
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      from.current = a + (target - a) * (1 - (1 - p) ** 3);
      setV(from.current);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

export function Num({ v, compact }: { v: number; compact?: boolean }) {
  const { f } = useApp();
  const x = useTween(v);
  return <>{compact ? f.c(x) : f.n(x)}</>;
}

type Pt = [number, number];
// horizontal-tangent cubic segments: smooth and never overshoots the data
const smooth = (p: Pt[]) =>
  p.reduce((d, [x, y], i) => {
    if (!i) return `M${x},${y}`;
    const [x0, y0] = p[i - 1], cx = (x0 + x) / 2;
    return `${d} C${cx},${y0} ${cx},${y} ${x},${y}`;
  }, "");
const useSvgId = () => "g" + useId().replace(/[^a-zA-Z0-9]/g, "");

export function Spark({ data, color = "var(--blue)", h = 36 }: { data: number[]; color?: string; h?: number }) {
  const id = useSvgId();
  const max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i): Pt => [(i / (data.length - 1 || 1)) * 100, h - 2 - ((v - min) / (max - min || 1)) * (h - 4)]);
  const line = smooth(pts);
  return (
    <svg className="spark" viewBox={`0 0 100 ${h}`} preserveAspectRatio="none" style={{ height: h }} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" style={{ stopColor: color, stopOpacity: 0.32 }} />
          <stop offset="1" style={{ stopColor: color, stopOpacity: 0 }} />
        </linearGradient>
      </defs>
      <path d={`${line} L100,${h} L0,${h}Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" style={{ stroke: color }} strokeWidth={1.8} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

type Series = (number | null)[];
type Line = { data: Series; color: string; label: string; dashed?: boolean; fill?: boolean };

/** Line/area chart. Nulls are allowed only at the ends of a series (contiguous data). */
export function Area({ lines, band, labels, h = 230 }: { lines: Line[]; band?: { lo: Series; hi: Series; color: string }; labels: string[]; h?: number }) {
  const { f, lang } = useApp();
  const id = useSvgId();
  const [hover, setHover] = useState<number | null>(null);
  const n = labels.length;
  const max = Math.max(1, ...[...lines.flatMap((l) => l.data), ...(band?.hi ?? [])].filter((v): v is number => v != null)) * 1.12;
  const pct = (i: number) => (i / (n - 1 || 1)) * 100;
  const pts = (d: Series) => d.flatMap((v, i): Pt[] => (v == null ? [] : [[pct(i) * 10, h - (v / max) * h]]));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((q) => Math.round(q * (n - 1)));

  return (
    <div className="chart"
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        setHover(Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left) / r.width) * (n - 1)))));
      }}
      onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 1000 ${h}`} preserveAspectRatio="none" style={{ height: h }} aria-hidden="true">
        <defs>
          {lines.map((l, k) => (
            <linearGradient key={k} id={`${id}${k}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" style={{ stopColor: l.color, stopOpacity: 0.28 }} />
              <stop offset="1" style={{ stopColor: l.color, stopOpacity: 0 }} />
            </linearGradient>
          ))}
        </defs>
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} x1="0" x2="1000" y1={h * g} y2={h * g} className="gridline" vectorEffect="non-scaling-stroke" />
        ))}
        {band && (() => {
          const hi = pts(band.hi), lo = pts(band.lo).reverse();
          return hi.length > 1 && <path d={`${smooth(hi)} ${smooth(lo).replace(/^M/, "L")}Z`} style={{ fill: band.color, opacity: 0.14 }} />;
        })()}
        {lines.map((l, k) => {
          const p = pts(l.data), d = smooth(p);
          return p.length > 1 && (
            <g key={k}>
              {l.fill && <path d={`${d} L${p.at(-1)![0]},${h} L${p[0][0]},${h}Z`} fill={`url(#${id}${k})`} />}
              <path d={d} fill="none" style={{ stroke: l.color }} strokeWidth={2.4} strokeLinecap="round"
                strokeDasharray={l.dashed ? "5 6" : undefined} vectorEffect="non-scaling-stroke" />
            </g>
          );
        })}
      </svg>
      {hover != null && (
        <>
          <div className="cursor" style={{ left: `${pct(hover)}%`, height: h }} />
          {lines.map((l) => l.data[hover] != null && (
            <i key={l.label} className="dot" style={{ left: `${pct(hover)}%`, top: h - (l.data[hover]! / max) * h, background: l.color }} />
          ))}
          <div className="tip" dir={lang === "fa" ? "rtl" : "ltr"} style={{ left: `clamp(70px, ${pct(hover)}%, calc(100% - 70px))` }}>
            <b>{labels[hover]}</b>
            {lines.map((l) => l.data[hover] != null && (
              <div key={l.label}><i style={{ background: l.color }} />{l.label} <b>{f.n(l.data[hover]!)}</b></div>
            ))}
          </div>
        </>
      )}
      <div className="x">{ticks.map((i, k) => <span key={k}>{labels[i]}</span>)}</div>
    </div>
  );
}

export function Bars({ data, h = 120 }: { data: number[]; h?: number }) {
  const max = Math.max(...data, 1);
  return (
    <div className="bars" style={{ height: h }} aria-hidden="true">
      {data.map((v, i) => <span key={i} style={{ height: `${Math.max(3, (v / max) * 100)}%` }} />)}
    </div>
  );
}

export function Donut({ items, children }: { items: { key: string; value: number }[]; children: ReactNode }) {
  const total = items.reduce((s, x) => s + x.value, 0) || 1;
  const R = 42, C = 2 * Math.PI * R;
  let acc = 0;
  return (
    <div className="donut">
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="50" r={R} fill="none" strokeWidth="11" style={{ stroke: "var(--fill)" }} />
        {items.map((it) => {
          const len = (it.value / total) * C, off = acc;
          acc += len;
          return (
            <circle key={it.key} cx="50" cy="50" r={R} fill="none" strokeWidth="11" style={{ stroke: COLORS[it.key] }}
              strokeDasharray={`${Math.max(len - 1.4, 0)} ${C}`} strokeDashoffset={-off} />
          );
        })}
      </svg>
      <div className="center">{children}</div>
    </div>
  );
}

export function HBar({ label, value, max, color, right }: { label: ReactNode; value: number; max: number; color: string; right: ReactNode }) {
  return (
    <div className="hbar" style={{ ["--c" as string]: color }}>
      <span>{label}</span>
      <b>{right}</b>
      <div className="track"><b style={{ width: `${(value / (max || 1)) * 100}%` }} /></div>
    </div>
  );
}
