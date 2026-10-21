// Headless-Chrome audit for the dashboard: screenshot, CPU cost over a window, tap-target and contrast checks.
//   node scripts/ui-audit.mjs <url> <out-prefix> [--dark] [--reduce] [--mobile] [--lang=en] [--measure=12]
// Talks to Chrome over the DevTools protocol using Node's built-in WebSocket. Loopback only.
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, out, ...flags] = process.argv.slice(2);
if (!url || !out) throw new Error("usage: ui-audit.mjs <url> <out-prefix> [--dark] [--reduce] [--mobile] [--lang=en] [--measure=12]");
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) throw new Error("loopback targets only");
const has = (f) => flags.includes(f);
const arg = (k, d) => (flags.find((f) => f.startsWith(`--${k}=`)) ?? `=${d}`).split("=")[1];
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "ui-audit-"))}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
try {
  let targets;
  for (let i = 0; i < 60 && !targets; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch { await sleep(500); }
  }
  const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  let id = 0; const pending = new Map(); const logs = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) pending.get(d.id)(d.result ?? d.error);
    if (d.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(d.params.type)) logs.push(d.params.args.map((a) => a.value ?? a.description).join(" "));
    if (d.method === "Log.entryAdded" && d.params.entry.level !== "info") logs.push(`${d.params.entry.source}: ${d.params.entry.text}`);
  };
  const send = (method, params = {}) => new Promise((res) => { pending.set(++id, res); ws.send(JSON.stringify({ id, method, params })); });
  const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result?.value;

  const [w, h] = has("--mobile") ? [390, 844] : [1440, 1000];
  await Promise.all(["Page.enable", "Runtime.enable", "Log.enable", "Performance.enable", "Network.enable"].map((m) => send(m)));
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: has("--mobile") });
  if (has("--mobile")) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Emulation.setEmulatedMedia", { features: [
    { name: "prefers-color-scheme", value: has("--dark") ? "dark" : "light" },
    { name: "prefers-reduced-motion", value: has("--reduce") ? "reduce" : "no-preference" },
  ] });
  const origin = new URL(url).origin;
  for (const [name, value] of [["theme", has("--dark") ? "dark" : "light"], ["lang", arg("lang", "fa")]])
    await send("Network.setCookie", { name, value, url: origin });
  await send("Page.navigate", { url });
  await sleep(6000);

  const metrics = async () => Object.fromEntries((await send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
  const m0 = await metrics(); const secs = Number(arg("measure", 12)); await sleep(secs * 1000); const m1 = await metrics();
  const d = (k) => +(((m1[k] - m0[k]) / secs) * 1000).toFixed(1); // seconds of CPU per second -> ms per second
  const cpu = { window_s: secs, task_ms_per_s: d("TaskDuration"), script_ms_per_s: d("ScriptDuration"), layout_ms_per_s: d("LayoutDuration"), style_ms_per_s: d("RecalcStyleDuration") };

  const dom = await evaluate(`(() => {
    const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== "hidden"; };
    const targets = [...document.querySelectorAll("a[href], button, [role=radio], textarea, [tabindex]:not([tabindex='-1'])")].filter((e) => vis(e) && e.getBoundingClientRect().bottom > 0);
    const small = targets.map((e) => { const r = e.getBoundingClientRect(); return { t: (e.getAttribute("aria-label") || e.textContent || e.tagName).trim().slice(0, 24), w: Math.round(r.width), h: Math.round(r.height) }; }).filter((x) => x.h < 44 || x.w < 44);
    const lum = (c) => { const [r, g, b] = c.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const rgba = (s) => { const n = (s.match(/[\\d.]+(?:e-?\\d+)?/g) || []).map(Number); return s.startsWith("color(") ? [n[0] * 255, n[1] * 255, n[2] * 255, ...(n.length > 3 ? [n[3]] : [])] : n; };
    const bgOf = (e) => { for (let n = e; n; n = n.parentElement) { const c = rgba(getComputedStyle(n).backgroundColor); if (c.length === 3 || (c.length === 4 && c[3] > 0.6)) return c.slice(0, 3); } return [255, 255, 255]; };
    const low = [];
    for (const e of document.querySelectorAll("p, span, small, b, h1, h2, a, button, div")) {
      if (![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) || !vis(e)) continue;
      const s = getComputedStyle(e); if (s.webkitTextFillColor === "rgba(0, 0, 0, 0)" || s.color === "rgba(0, 0, 0, 0)") continue;
      const fg = rgba(s.color); const bg = bgOf(e); if (fg.length < 3) continue;
      const a = fg[3] ?? 1; const f = fg.slice(0, 3).map((v, i) => v * a + bg[i] * (1 - a));
      const L1 = lum(f), L2 = lum(bg); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const size = parseFloat(s.fontSize), bold = +s.fontWeight >= 700; const need = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5;
      if (ratio < need) low.push({ t: e.textContent.trim().slice(0, 28), ratio: +ratio.toFixed(2), need, px: size });
    }
    const uniq = (xs) => [...new Map(xs.map((x) => [x.t + (x.ratio ?? x.w + "x" + x.h), x])).values()];
    return { targets: targets.length, small: uniq(small), lowContrast: uniq(low).sort((a, b) => a.ratio - b.ratio).slice(0, 14),
      landmarks: { nav: document.querySelectorAll("nav").length, navLabelled: document.querySelectorAll("nav[aria-label]").length, main: document.querySelectorAll("main").length,
        current: document.querySelectorAll("[aria-current]").length, live: document.querySelectorAll("[aria-live],[role=status],[role=alert]").length, skip: document.querySelectorAll("a.skip").length },
      backdropLayers: [...document.querySelectorAll("*")].filter((e) => { const s = getComputedStyle(e); return s.backdropFilter !== "none" || s.webkitBackdropFilter !== "none" && s.webkitBackdropFilter; }).length,
      infiniteAnims: document.getAnimations().filter((a) => a.effect.getComputedTiming().iterations === Infinity).length };
  })()`);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${out}.png`, Buffer.from(shot.data, "base64"));
  const report = { url, viewport: `${w}x${h}`, flags, cpu, ...dom, consoleProblems: [...new Set(logs)].slice(0, 8) };
  writeFileSync(`${out}.json`, JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
  ws.close();
} finally { chrome.kill(); }
