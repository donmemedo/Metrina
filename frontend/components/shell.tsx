"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { dict, makeFmt, type Dict, type Fmt, type Lang, type Theme } from "@/lib/i18n";

type Ctx = { lang: Lang; theme: Theme; t: Dict; f: Fmt; setLang(l: Lang): void; setTheme(t: Theme, e?: MouseEvent): void };
const AppCtx = createContext<Ctx>(null!);
export const useApp = () => useContext(AppCtx);

const save = (k: string, v: string) => (document.cookie = `${k}=${v};path=/;max-age=31536000;samesite=lax`);
const calm = () => !document.startViewTransition || matchMedia("(prefers-reduced-motion: reduce)").matches;

export function usePoll<T>(url: string, ms: number) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<number | null>(null); // HTTP status, 0 = network
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(url)
        .then(async (r) => {
          if (!r.ok) throw r.status;
          const j = await r.json();
          if (alive) (setData(j), setError(null));
        })
        .catch((e) => alive && setError(typeof e === "number" ? e : 0));
    load();
    const id = setInterval(() => !document.hidden && load(), ms);
    return () => ((alive = false), clearInterval(id));
  }, [url, ms]);
  return { data, error };
}

const PATHS = {
  grid: "M4 5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zM13 5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1zM4 14a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zM13 14a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1z",
  chat: "M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z",
  code: "M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 4l-3 16",
  sun: "M12 3v1.5M12 19.5V21M3 12h1.5M19.5 12H21M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M5.6 18.4l1.1-1.1M17.3 6.7l1.1-1.1M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  moon: "M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z",
  auto: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 3v18M12 7h4M12 11h5M12 15h4",
  globe: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.5 9h17M3.5 15h17M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9c-2.4-2.5-3.6-5.5-3.6-9S9.6 5.5 12 3z",
  leaf: "M5 19c0-8.5 6-14 15-14 0 9-5.5 15-14 15zM5 19l8-8",
  back: "M15 18l-6-6 6-6",
  up: "M7 17L17 7M9 7h8v8",
  down: "M7 7l10 10M17 9v8H9",
  copy: "M9 9h10v10H9zM5 15V5h10",
  spark: "M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
  send: "M4 12l16-8-6 16-2.5-6.5z",
  check: "M5 12.5l4.5 4.5L19 7.5",
};
export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  );
}

const NAV = [
  ["/", "grid", "nav_dash"],
  ["/voice", "chat", "nav_voice"],
  ["/setup", "code", "nav_setup"],
] as const;
const THEMES = [["system", "auto"], ["light", "sun"], ["dark", "moon"]] as const;

export function Shell({ lang: lang0, theme: theme0, children }: { lang: Lang; theme: Theme; children: ReactNode }) {
  const [lang, setL] = useState(lang0);
  const [theme, setT] = useState(theme0);
  const path = usePathname();
  const t = dict[lang];

  const value = useMemo<Ctx>(() => ({
    lang, theme, t: dict[lang], f: makeFmt(lang),
    setLang(l) {
      save("lang", l);
      const apply = () => {
        document.documentElement.lang = l;
        document.documentElement.dir = l === "fa" ? "rtl" : "ltr";
        flushSync(() => setL(l));
      };
      calm() ? apply() : document.startViewTransition(apply);
    },
    setTheme(next, e) {
      save("theme", next);
      const apply = () => {
        const el = document.documentElement;
        if (next === "system") delete el.dataset.theme;
        else el.dataset.theme = next;
        flushSync(() => setT(next));
      };
      if (calm()) return apply();
      // circular reveal from the tap point
      const x = e?.clientX ?? innerWidth / 2, y = e?.clientY ?? 0;
      const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      document.startViewTransition(apply).ready.then(() =>
        document.documentElement.animate(
          { clipPath: [`circle(0 at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
          { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)", pseudoElement: "::view-transition-new(root)" },
        ),
      );
    },
  }), [lang, theme]);

  useEffect(() => void (document.title = `${t.brand} · ${t.tagline}`), [t]);
  const on = (href: string) => (href === "/" ? path === "/" || path.startsWith("/posts") : path.startsWith(href));

  return (
    <AppCtx.Provider value={value}>
      <header className="top wrap">
        <div className="bar">
          <Link href="/" className="brand" aria-label={t.brand}>
            <span className="logo"><Icon name="leaf" size={18} /></span>
            <b>{t.brand}</b>
          </Link>
          <nav className="seg nav">
            {NAV.map(([href, icon, key]) => (
              <Link key={href} href={href} className={on(href) ? "on" : ""}>
                <Icon name={icon} size={16} />{t[key]}
              </Link>
            ))}
          </nav>
          <div className="controls">
            <button className="pill-btn" onClick={() => value.setLang(lang === "fa" ? "en" : "fa")} aria-label={t.language}>
              <Icon name="globe" size={16} />{lang === "fa" ? "EN" : "فا"}
            </button>
            <div className="seg" role="radiogroup" aria-label={t.theme}>
              {THEMES.map(([m, icon]) => (
                <button key={m} role="radio" aria-checked={theme === m} className={theme === m ? "on" : ""}
                  onClick={(e) => value.setTheme(m, e)} title={t[`theme_${m}`]} aria-label={t[`theme_${m}`]}>
                  <Icon name={icon} size={15} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>
      <main className="wrap">{children}</main>
      <nav className="tabbar">
        {NAV.map(([href, icon, key]) => (
          <Link key={href} href={href} className={on(href) ? "on" : ""}>
            <Icon name={icon} size={22} />{t[key]}
          </Link>
        ))}
      </nav>
    </AppCtx.Provider>
  );
}
