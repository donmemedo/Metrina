"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { CSSProperties } from "react";
import { Area, COLORS, HBar, Num } from "@/components/charts";
import { Icon, useApp, usePoll } from "@/components/shell";
import { label } from "@/lib/i18n";

type Post = {
  id: string; title_fa: string; title_en: string; section: string | null; author_fa: string; author_en: string;
  published: number; readers: number; history: number[]; forecast: number[]; low: number[]; high: number[];
  total: number; forecast_total: number; stage: "rising" | "peak" | "decaying" | "evergreen"; engaged: number;
  referrers: { key: string; value: number }[];
};
const STAGE_COLOR = { rising: "var(--green)", peak: "var(--orange)", decaying: "var(--pink)", evergreen: "var(--teal)" };
const vars = (o: Record<string, string | number>) => o as CSSProperties;

export default function PostPage() {
  const { id } = useParams<{ id: string }>();
  const { t, f, lang } = useApp();
  const { data: p, error } = usePoll<Post>(`/api/posts/${id}`, 10000);
  const back = <Link href="/" className="back"><Icon name="back" size={18} className="flip" />{t.back}</Link>;

  if (error === 404) return <>{back}<div className="card"><h2>{t.not_found}</h2></div></>;
  if (!p)
    return (
      <>
        {back}
        {error != null && <div className="banner">{t.offline}</div>}
        <div className="grid"><div className="skel s12" style={{ height: 160 }} /><div className="skel s12" style={{ height: 380 }} /></div>
      </>
    );

  const H = p.history.length;
  const hourMs = Math.floor(Date.now() / 3.6e6) * 3.6e6;
  const labels = Array.from({ length: H + 24 }, (_, i) => f.hour(hourMs + (i - H + 1) * 3.6e6));
  const pad = (n: number) => Array<null>(n).fill(null);
  const joined = (xs: number[]) => [...pad(H - 1), p.history[H - 1], ...xs];
  const refMax = Math.max(...p.referrers.map((r) => r.value), 1);

  return (
    <div className="story">
      {back}
      {error != null && <div className="banner">{t.offline}</div>}
      <div className="grid">
        <section className="card s12 rise" style={vars({ "--i": 0 })}>
          <div className="meta">
            {p.section && <span className="pill" style={vars({ "--c": COLORS[p.section] })}>{label(t, "sec", p.section)}</span>}
            <span className="pill stage" style={vars({ "--c": STAGE_COLOR[p.stage] })}>{label(t, "stage", p.stage)}</span>
          </div>
          <h1>{lang === "fa" ? p.title_fa : p.title_en}</h1>
          <div className="meta">{t.by} {lang === "fa" ? p.author_fa : p.author_en} · {f.ago(p.published)}</div>
        </section>

        <div className="kpis s12">
          {([
            ["spark", "var(--blue)", t.total_views, <Num key="a" v={p.total} compact />],
            ["up", "var(--purple)", t.next24, <Num key="b" v={p.forecast_total} compact />],
            ["clock", "var(--orange)", t.engaged, f.dur(p.engaged)],
            ["globe", "var(--green)", t.readers_now, <Num key="d" v={p.readers} />],
          ] as const).map(([icon, c, name, value], i) => (
            <div key={name} className="card kpi rise" style={vars({ "--i": i + 1, "--c": c })}>
              <span className="kpi-icon"><Icon name={icon} size={16} /></span>
              <span className="label">{name}</span>
              <span className="value">{value}</span>
            </div>
          ))}
        </div>

        <section className="card rec s12 rise" style={vars({ "--i": 5 })}>
          <span className="kpi-icon"><Icon name="spark" size={16} /></span>
          <div><h2>{t.rec_title}</h2><p>{label(t, "rec", p.stage)}</p></div>
        </section>

        <section className="card s8 rise" style={vars({ "--i": 6 })}>
          <div className="head">
            <div><h2>{t.lifecycle}</h2><p className="sub">{t.lifecycle_sub}</p></div>
            <div className="legend">
              <span><i style={{ background: "var(--blue)" }} />{t.actual}</span>
              <span><i className="dash" style={{ color: "var(--purple)" }} />{t.forecast}</span>
            </div>
          </div>
          <Area labels={labels}
            band={{ lo: joined(p.low), hi: joined(p.high), color: "var(--purple)" }}
            lines={[
              { data: [...p.history, ...pad(24)], color: "var(--blue)", label: t.actual, fill: true },
              { data: joined(p.forecast), color: "var(--purple)", label: t.forecast, dashed: true },
            ]} />
        </section>

        <section className="card s4 rise" style={vars({ "--i": 7 })}>
          <div className="head"><div><h2>{t.referrers}</h2><p className="sub">{t.referrers_sub}</p></div></div>
          {[...p.referrers].sort((a, b) => b.value - a.value).map((r) => (
            <HBar key={r.key} label={label(t, "ref", r.key)} value={r.value} max={refMax} color={COLORS[r.key]} right={f.c(r.value)} />
          ))}
        </section>
      </div>
    </div>
  );
}
