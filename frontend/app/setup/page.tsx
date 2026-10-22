"use client";
import { useEffect, useState, type CSSProperties } from "react";
import { Icon, useApp } from "@/components/shell";

const API = [
  ["GET", "/api/overview", "api_overview", "var(--blue)"],
  ["GET", "/api/posts/{id}", "api_post", "var(--blue)"],
  ["POST", "/api/nlp", "api_nlp", "var(--green)"],
  ["POST", "/api/track", "api_track", "var(--green)"],
] as const;

export default function Setup() {
  const { t } = useApp();
  const [origin, setOrigin] = useState("https://parsely.example");
  const [done, setDone] = useState<"copy" | "sent" | null>(null);
  useEffect(() => setOrigin(location.origin), []);
  const flash = (k: "copy" | "sent") => (setDone(k), setTimeout(() => setDone(null), 1800));
  const snippet = `<script async src="${origin}/tracker.js"></script>`;

  return (
    <>
      <div className="page-head rise">
        <h1><span>{t.setup_title}</span></h1>
        <p>{t.setup_sub}</p>
      </div>
      <div className="grid">
        <section className="card s7 rise" style={{ "--i": 1 } as CSSProperties}>
          <pre className="code">
            <span className="t">&lt;script</span> <span className="a">async src</span>=<span className="s">&quot;{origin}/tracker.js&quot;</span><span className="t">&gt;&lt;/script&gt;</span>
          </pre>
          <div className="actions">
            <button className="btn" onClick={() => navigator.clipboard?.writeText(snippet).then(() => flash("copy"), () => {})}>
              <Icon name={done === "copy" ? "check" : "copy"} size={16} /><span aria-live="polite">{done === "copy" ? t.copied : t.copy}</span>
            </button>
            <button className="btn ghost" onClick={() =>
              fetch("/api/track", {
                method: "POST",
                body: JSON.stringify({ url: "/demo", title: t.test_event, referrer: "https://t.me/parsely", host: location.host }),
              }).then((r) => r.ok && flash("sent"), () => {})}>
              <Icon name={done === "sent" ? "check" : "send"} size={16} /><span aria-live="polite">{done === "sent" ? t.sent : t.test_event}</span>
            </button>
          </div>
        </section>
        <section className="card s5 rise" style={{ "--i": 2 } as CSSProperties}>
          <div className="head"><h2>{t.api_title}</h2></div>
          <div className="api">
            {API.map(([m, path, key, c]) => (
              <div key={path}>
                <span className="method" style={{ "--c": c } as CSSProperties}>{m}</span>
                <code>{path}</code>
                <span>{t[key]}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
