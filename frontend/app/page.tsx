"use client";
import Link from "next/link";
import type { CSSProperties } from "react";
import { Area, Bars, COLORS, Donut, HBar, Num, Spark } from "@/components/charts";
import { Icon, useApp, usePoll, useSlow, type IconName } from "@/components/shell";
import { label } from "@/lib/i18n";

type Row = {
  id: string; title_fa: string; title_en: string; section: string | null; author_fa: string; author_en: string;
  published: number; readers: number; views_30m: number; views_24h: number; spark: number[];
};
type KV = { key: string; value: number };
type Overview = {
  readers: number; pageviews: number; visitors: number; change: number; engaged: number; posts: number;
  series: number[]; prev_series: number[]; realtime: number[]; referrers: KV[]; devices: KV[]; sections: KV[]; top: Row[];
};

const vars = (o: Record<string, string | number>) => o as CSSProperties;

function Kpi({ i, icon, color, name, value, change, spark }: {
  i: number; icon: IconName; color: string; name: string; value: React.ReactNode; change?: number; spark?: number[];
}) {
  const { f, t } = useApp();
  return (
    <div className="card kpi rise" style={vars({ "--i": i, "--c": color })}>
      <span className="kpi-icon"><Icon name={icon} size={16} /></span>
      <span className="label">{name}</span>
      <span className="value">{value}</span>
      {change != null && (
        <span className={`chip ${change >= 0 ? "up" : "down"}`} title={t.vs_yesterday}>
          <Icon name={change >= 0 ? "up" : "down"} size={12} />{f.pct(change)} <span className="muted">&nbsp;{t.vs_yesterday}</span>
        </span>
      )}
      {spark && <Spark data={spark} color={color} />}
    </div>
  );
}

export default function Dashboard() {
  const { t, f, lang } = useApp();
  const { data: d, error } = usePoll<Overview>("/api/overview", 3000);
  const slow = useSlow(d ? { r: d.readers, p: d.pageviews } : null, 30000); // announced at most every 30 s

  if (!d)
    return (
      <>
        {error != null && <div className="banner" role="alert">{t.offline}</div>}
        <div className="grid" aria-busy="true">
          <p className="sr-only" role="status">{t.loading}</p>
          {[["s12", 300], ["s8", 340], ["s4", 340], ["s8", 480], ["s4", 480]].map(([c, h], i) => (
            <div key={i} className={`skel ${c}`} style={{ height: h }} />
          ))}
        </div>
      </>
    );

  const now = Date.now();
  const hours = d.series.map((_, i) => f.hour(Math.floor(now / 3.6e6) * 3.6e6 - (23 - i) * 3.6e6));
  const refTotal = d.referrers.reduce((s, r) => s + r.value, 0);
  const devTotal = d.devices.reduce((s, r) => s + r.value, 0) || 1;
  const topMax = Math.max(...d.top.map((r) => r.views_30m), 1);

  return (
    <>
      {error != null && <div className="banner" role="alert">{t.offline}</div>}
      {slow && <p className="sr-only" role="status">{f.n(slow.r)} {t.readers_now}. {t.pageviews}: {f.n(slow.p)}</p>}
      <div className="grid">
        <section className="card hero s12 rise" style={vars({ "--i": 0 })}>
          <div>
            <span className="live"><i />{t.live}</span>
            <div className="mega"><Num v={d.readers} /></div>
            <p>{t.readers_sub}</p>
          </div>
          <div>
            <div className="side-head"><span>{t.last30}</span><b><Num v={d.realtime.reduce((a, b) => a + b, 0)} /></b></div>
            <Bars data={d.realtime} h={130} />
            <div className="axis"><span>{t.min_ago}</span><span>{t.now}</span></div>
          </div>
        </section>

        <div className="kpis s12">
          <Kpi i={1} icon="spark" color="var(--blue)" name={t.pageviews} value={<Num v={d.pageviews} compact />} change={d.change} spark={d.series} />
          <Kpi i={2} icon="globe" color="var(--purple)" name={t.visitors} value={<Num v={d.visitors} compact />} spark={d.series.map((v) => v * 0.61)} />
          <Kpi i={3} icon="clock" color="var(--orange)" name={t.engaged} value={f.dur(d.engaged)} />
          <Kpi i={4} icon="grid" color="var(--pink)" name={t.posts} value={<Num v={d.posts} />} />
        </div>

        <section className="card s8 rise" style={vars({ "--i": 5 })}>
          <div className="head">
            <div><h2>{t.traffic}</h2><p className="sub">{t.traffic_sub}</p></div>
            <div className="legend">
              <span><i style={{ background: "var(--blue)" }} />{t.today}</span>
              <span><i className="dash" style={{ color: "var(--gray)" }} />{t.yesterday}</span>
            </div>
          </div>
          <Area h={300} name={t.traffic} labels={hours} lines={[
            { data: d.prev_series, color: "var(--gray)", label: t.yesterday, dashed: true },
            { data: d.series, color: "var(--blue)", label: t.today, fill: true },
          ]} />
        </section>

        <section className="card s4 rise" style={vars({ "--i": 6 })}>
          <div className="head"><div><h2>{t.referrers}</h2><p className="sub">{t.referrers_sub}</p></div></div>
          <Donut items={d.referrers}><b><Num v={refTotal} /></b><small>{t.views}</small></Donut>
          <div className="legend-grid">
            {[...d.referrers].sort((a, b) => b.value - a.value).map((r) => (
              <span key={r.key}><i style={{ background: COLORS[r.key] }} />{label(t, "ref", r.key)}<b>{f.share(r.value / (refTotal || 1))}</b></span>
            ))}
          </div>
        </section>

        <section className="card s8 rise" style={vars({ "--i": 7 })}>
          <div className="head"><div><h2>{t.top_posts}</h2><p className="sub">{t.top_sub}</p></div></div>
          <div className="posts">
            {d.top.map((p, i) => (
              <Link key={p.id} href={`/posts/${p.id}`} className="post">
                <span className="rank">{f.n(i + 1)}</span>
                <div style={{ minWidth: 0 }}>
                  <div className="title">{lang === "fa" ? p.title_fa : p.title_en}</div>
                  <div className="meta">
                    {p.section && <span className="pill" style={vars({ "--c": COLORS[p.section] })}>{label(t, "sec", p.section)}</span>}
                    <span>{lang === "fa" ? p.author_fa : p.author_en}</span>·<span>{f.ago(p.published)}</span>
                  </div>
                  <div className="meter"><b style={{ width: `${(p.views_30m / topMax) * 100}%` }} /></div>
                </div>
                <div className="spark-cell"><Spark data={p.spark} color={COLORS[p.section ?? "tech"]} h={30} /></div>
                <div className="num"><Num v={p.readers} /><small>{t.readers}</small></div>
              </Link>
            ))}
          </div>
        </section>

        <section className="card s4 rise" style={vars({ "--i": 8 })}>
          <div className="head"><div><h2>{t.sections}</h2><p className="sub">{t.sections_sub}</p></div></div>
          {d.sections.map((s) => (
            <HBar key={s.key} label={label(t, "sec", s.key)} value={s.value} max={d.sections[0]?.value ?? 1} color={COLORS[s.key]} right={f.c(s.value)} />
          ))}
          <h2 style={{ marginTop: 26 }}>{t.devices}</h2>
          <div className="stack">
            {d.devices.map((x) => <b key={x.key} style={{ flexGrow: x.value / devTotal, background: COLORS[x.key] }} />)}
          </div>
          <div className="legend">
            {d.devices.map((x) => (
              <span key={x.key}><i style={{ background: COLORS[x.key] }} />{label(t, "dev", x.key)} {f.share(x.value / devTotal)}</span>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
