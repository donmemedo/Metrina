"use client";
import { useState, type CSSProperties } from "react";
import { Icon, useApp } from "@/components/shell";

type Result = {
  words: number; sentences: number; reading_sec: number; keywords: { term: string; count: number }[];
  sentiment: { score: number; positive: number; negative: number }; questions: string[];
};
const KW = ["var(--blue)", "var(--purple)", "var(--pink)", "var(--orange)", "var(--green)", "var(--teal)", "var(--indigo)"];

export default function Voice() {
  const { t, f } = useApp();
  const [text, setText] = useState("");
  const [res, setRes] = useState<Result>();
  const [state, setState] = useState<"idle" | "busy" | "empty" | "error">("idle");

  async function run(value = text) {
    if (!value.trim()) return setState("empty");
    setState("busy");
    try {
      const r = await fetch("/api/nlp", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: value }) });
      if (!r.ok) throw 0;
      setRes(await r.json());
      setState("idle");
    } catch {
      setState("error");
    }
  }

  const s = res?.sentiment.score ?? 0;
  const mood = s > 0.2 ? t.positive : s < -0.2 ? t.negative : t.neutral;
  const maxKw = res?.keywords[0]?.count ?? 1;

  return (
    <>
      <div className="page-head rise">
        <h1><span>{t.voice_title}</span></h1>
        <p>{t.voice_sub}</p>
      </div>
      <div className="grid">
        <section className="card s12 rise" style={{ "--i": 1 } as CSSProperties}>
          <textarea value={text} placeholder={t.placeholder} aria-label={t.placeholder} aria-invalid={state === "empty"}
            onChange={(e) => (setText(e.target.value), state === "empty" && setState("idle"))} maxLength={20000} />
          <div className="actions">
            <button className="btn" onClick={() => run()} disabled={state === "busy"}><Icon name="spark" size={16} />{t.analyze}</button>
            <button className="btn ghost" onClick={() => (setText(t.sample_text), run(t.sample_text))}>{t.sample}</button>
            {state === "empty" && <span className="error" role="alert">{t.empty}</span>}
            {state === "error" && <span className="error" role="alert">{t.offline}</span>}
          </div>
        </section>

        <p className="sr-only" role="status">{state === "busy" ? t.loading : res ? `${t.sentiment}: ${mood}` : ""}</p>
        {res && (
          <>
            <section className="card s5 rise" style={{ "--i": 0 } as CSSProperties}>
              <h2>{t.sentiment}</h2>
              <div className="big-label" style={{ color: s > 0.2 ? "var(--green)" : s < -0.2 ? "var(--red)" : "var(--orange)" }}>{mood}</div>
              <div className="senti"><i style={{ "--x": `${((s + 1) / 2) * 100}%` } as CSSProperties} /></div>
              <div className="senti-labels"><span>{t.negative} · {f.n(res.sentiment.negative)}</span><span>{t.positive} · {f.n(res.sentiment.positive)}</span></div>
              <div className="stats" style={{ marginTop: 20 }}>
                <div className="stat"><b>{f.n(res.words)}</b><span>{t.words}</span></div>
                <div className="stat"><b>{f.n(res.sentences)}</b><span>{t.sentences}</span></div>
                <div className="stat"><b>{f.dur(res.reading_sec)}</b><span>{t.reading}</span></div>
              </div>
            </section>
            <section className="card s7 rise" style={{ "--i": 1 } as CSSProperties}>
              <div className="head"><h2>{t.keywords}</h2></div>
              <div className="chips">
                {res.keywords.map((k, i) => (
                  <span key={k.term} className="kw" style={{ "--c": KW[i % KW.length], "--w": k.count / maxKw, "--i": i } as CSSProperties}>
                    {k.term} <small>{f.n(k.count)}</small>
                  </span>
                ))}
              </div>
            </section>
            <section className="card s12 rise" style={{ "--i": 2 } as CSSProperties}>
              <div className="head"><h2>{t.questions}</h2></div>
              {res.questions.length ? (
                <ul className="qs">{res.questions.map((q) => <li key={q}><Icon name="chat" size={16} />{q}</li>)}</ul>
              ) : <p className="muted">{t.no_questions}</p>}
            </section>
          </>
        )}
      </div>
    </>
  );
}
