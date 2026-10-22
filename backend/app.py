"""Parsely Iran — content analytics API: live event collector, lifecycle forecast, Persian NLP."""
import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import random
import re
import time
import zlib
from collections import Counter, deque
from contextlib import asynccontextmanager, suppress
from functools import lru_cache
from statistics import linear_regression, pstdev
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

API_TOKEN = os.environ.get("API_TOKEN", "")  # when set, read endpoints need "Authorization: Bearer <token>"
TRUST_PROXY = os.environ.get("TRUST_PROXY") == "1"  # client IP = last X-Forwarded-For entry; ONLY behind an edge proxy that overwrites it (Caddy in compose). Next alone passes client values through.
API_DOCS = os.environ.get("API_DOCS") == "1"  # Swagger UI is off unless asked for
MAX_POSTS = 500
LIMITS = {"/api/track": (4096, 120), "/api/nlp": (65536, 30)}  # path -> (max body bytes, requests per minute per IP)
READ_PER_MIN = 600  # GET /api/*, shared per IP: one dashboard tab polls about 25 times a minute
log = logging.getLogger("parsely")

REFERRERS = ["google", "telegram", "instagram", "x", "direct", "internal"]
DEVICES = ["mobile", "desktop", "tablet"]
AUTHORS = [("سارا احمدی", "Sara Ahmadi"), ("علی رضایی", "Ali Rezaei"), ("مریم کریمی", "Maryam Karimi"),
           ("رضا موسوی", "Reza Mousavi"), ("نگار حسینی", "Negar Hosseini"), ("امید جعفری", "Omid Jafari")]
TITLES = {
    "politics": [("پشت پرده مذاکرات تازه؛ آنچه باید بدانید", "Behind the new negotiations: what you need to know"),
                 ("مجلس و بودجه ۱۴۰۶؛ پنج نکته کلیدی", "Parliament and the 1406 budget: five key points"),
                 ("انتخابات شوراها به کدام سمت می‌رود؟", "Where are the council elections heading?"),
                 ("روایت یک روز پرخبر در بهارستان", "One busy news day at Baharestan")],
    "economy": [("دلار امروز؛ بازار در انتظار تصمیم تازه", "Dollar today: the market awaits a new decision"),
                ("بورس تهران رکورد تازه زد", "Tehran Stock Exchange hits a new record"),
                ("اجاره‌بها در تهران؛ راهنمای مستاجران", "Tehran rents: a guide for tenants"),
                ("طلا یا مسکن؟ مقایسه بازدهی پنج‌ساله", "Gold or housing? Comparing five-year returns")],
    "tech": [("هوش مصنوعی فارسی‌زبان چقدر پیشرفت کرده؟", "How far has Persian-language AI come?"),
             ("راهنمای خرید گوشی میان‌رده در پاییز", "Mid-range phone buying guide for autumn"),
             ("استارتاپ‌های ایرانی و موج تازه سرمایه‌گذاری", "Iranian startups and a new wave of investment"),
             ("اینترنت ماهواره‌ای؛ واقعیت یا رویا؟", "Satellite internet: reality or dream?")],
    "sport": [("استقلال و پرسپولیس؛ پیش‌بازی داغ دربی", "Esteghlal vs Persepolis: a hot derby preview"),
              ("تیم ملی والیبال به فینال رسید", "National volleyball team reaches the final"),
              ("لیگ برتر؛ جدول در هفته دهم", "Pro League: the table after week ten"),
              ("ستاره جوان کشتی ایران کیست؟", "Who is Iran's young wrestling star?")],
    "culture": [("پرفروش‌ترین فیلم‌های پاییز در سینماها", "Autumn's box-office hits"),
                ("نمایشگاه کتاب؛ ده کتاب که نباید از دست داد", "Book fair: ten books you shouldn't miss"),
                ("موسیقی سنتی در نسل تازه", "Traditional music in a new generation"),
                ("سفر به یزد؛ شهر بادگیرها", "Travel to Yazd, the city of windcatchers")],
    "health": [("خواب خوب؛ هفت عادت ساده", "Good sleep: seven simple habits"),
               ("آلودگی هوا و راه‌های محافظت", "Air pollution and how to protect yourself"),
               ("رژیم مدیترانه‌ای برای ایرانی‌ها", "A Mediterranean diet for Iranians"),
               ("واکسن آنفلوآنزا؛ پرسش‌های پرتکرار", "Flu vaccine: frequently asked questions")],
}


def make_posts(start):
    rnd, posts = random.Random(7), {}  # nosec B311: seeded demo data, not a secret
    for sec, items in TITLES.items():
        for fa, en in items:
            pid = f"p{len(posts) + 1}"
            posts[pid] = dict(id=pid, title_fa=fa, title_en=en, section=sec, author=AUTHORS[len(posts) % 6],
                              published=start - rnd.uniform(0.4, 70) * 3600, peak=rnd.uniform(400, 6000),
                              tau=rnd.uniform(2, 9), k=rnd.uniform(1.2, 2.5), floor=rnd.uniform(0.03, 0.12),
                              engaged=rnd.randint(35, 190), refs=[rnd.random() + 0.2 for _ in REFERRERS])
    return posts


# ponytail: in-memory store, resets on restart; move to Postgres/ClickHouse when real customers send events
POSTS = make_posts(time.time())
TRACKED = Counter()  # (post id, hour index) -> real tracked pageviews
BUCKETS = deque(maxlen=30)  # one per minute: live pageviews by post / referrer / device
# No locks: every handler that touches the stores above is async, so it runs on the event loop and never interleaves with another.
# The one sync handler (/api/nlp) is pure and runs on the thread pool; keep it that way.


def model(p, age_h):
    """Lifecycle curve: gamma-shaped rise, peak at tau hours, then decay onto an evergreen floor."""
    if age_h <= 0 or not p["peak"]:
        return 0.0
    x = age_h / p["tau"]
    return p["peak"] * (x ** p["k"] * math.exp(p["k"] * (1 - x)) + p["floor"])


def season(t):
    h = (t / 3600 + 3.5) % 24  # Tehran local hour
    return 0.25 + 0.75 * max(0.0, math.sin(math.pi * (h - 6) / 18))


@lru_cache(maxsize=65536)
def synth(pid, hour):
    """Synthetic views for one (post, hour): lifecycle × daily rhythm × stable noise. Immutable, so cached."""
    p = POSTS[pid]
    noise = 0.85 + 0.3 * zlib.crc32(f"{pid}:{hour}".encode()) / 0xFFFFFFFF
    return round(model(p, hour - p["published"] / 3600) * season(hour * 3600) * noise)


def history(p, hours):
    h0 = int(time.time() // 3600)
    return [synth(p["id"], h) + TRACKED[p["id"], h] for h in range(h0 - hours + 1, h0 + 1)]


def new_bucket(minute):
    b = {"t": minute, "posts": Counter(), "refs": Counter(), "devices": Counter()}
    BUCKETS.append(b)
    return b


def bucket():
    m = int(time.time() // 60)
    return BUCKETS[-1] if BUCKETS and BUCKETS[-1]["t"] == m else new_bucket(m)


def record(b, pid, ref, dev):
    b["posts"][pid] += 1
    b["refs"][ref] += 1
    b["devices"][dev] += 1


def simulate(seconds, b, now=None):
    """Synthetic readers so the demo is alive before a real site is connected."""
    now = now or time.time()
    for p in POSTS.values():
        rate = model(p, (now - p["published"]) / 3600) * season(now) / 3600 * seconds
        for _ in range(int(rate) + (random.random() < rate % 1)):  # nosec B311: synthetic demo traffic
            record(b, p["id"], random.choices(REFERRERS, p["refs"])[0], random.choices(DEVICES, (62, 33, 5))[0])  # nosec B311


def evict():
    """Drop the tracked page with the fewest views this hour and last, so junk URLs push out each other, not real pages."""
    h = int(time.time() // 3600)
    victim = min((TRACKED[k, h] + TRACKED[k, h - 1], k) for k in POSTS if k[0] == "t")[1]
    del POSTS[victim]


def prune():
    """Hourly: forget tracked counts older than the 72 h any chart reads, and drop idle rate-limit rows."""
    h = int(time.time() // 3600)
    for key in [k for k in TRACKED if k[1] < h - 72]:
        del TRACKED[key]
    for key in [k for k, q in HITS.items() if not q or q[-1] < time.monotonic() - 60]:
        del HITS[key]


async def ticker():
    hour = int(time.time() // 3600)
    while True:
        simulate(2, bucket())
        if int(time.time() // 3600) != hour:
            hour = int(time.time() // 3600)
            prune()
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(_):
    m = int(time.time() // 60)
    for t in range(m - 29, m):
        simulate(60, new_bucket(t), t * 60)
    task = asyncio.create_task(ticker())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


# ---------- edge: body cap, rate limit, security headers (pure ASGI: no BaseHTTPMiddleware task-per-request cost) ----------
HITS = {}  # (ip, bucket) -> deque of request times within the last minute
EVENTS = Counter()  # denials by kind, logged at counts 1, 2, 4, 8, ... so a flood cannot also flood the log
DEFAULT_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"cache-control": b"no-store",
    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'",
    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
}


def sec_event(kind, ip, path):
    EVENTS[kind] += 1
    n = EVENTS[kind]
    if n & (n - 1) == 0:
        log.warning("security_event kind=%s ip=%s path=%s count=%d", kind, ip, path, n)


def client_ip(scope):
    peer = scope["client"][0] if scope.get("client") else "?"
    if TRUST_PROXY:  # the edge proxy overwrites X-Forwarded-For with the address it saw, so the last entry is ours
        fwd = [v for k, v in scope["headers"] if k == b"x-forwarded-for"]
        if fwd:
            return fwd[-1].decode("latin-1").split(",")[-1].strip()[:64] or peer
    return peer


def limited(ip, bucket, per_min):
    now = time.monotonic()
    if len(HITS) > 20000:  # ponytail: flush instead of LRU; an IP flood would otherwise grow this table unbounded
        HITS.clear()
    q = HITS.setdefault((ip, bucket), deque())
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= per_min:
        return True
    q.append(now)
    return False


class Guard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        https = scope.get("scheme") == "https" or (b"x-forwarded-proto", b"https") in scope["headers"]

        async def send_with_headers(msg):
            if msg["type"] == "http.response.start":
                have = {k for k, _ in msg["headers"]}
                extra = [(k, v) for k, v in DEFAULT_HEADERS.items() if k not in have]
                if https:
                    extra.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains"))
                msg = {**msg, "headers": list(msg["headers"]) + extra}
            await send(msg)

        path, method, headers = scope["path"], scope["method"], scope["headers"]
        if method == "POST" and path in LIMITS:
            max_body, per_min = LIMITS[path]
            length = next((v for k, v in headers if k == b"content-length"), None)
            if length is None or any(k == b"transfer-encoding" for k, _ in headers):
                # the cap trusts Content-Length and chunked framing would ignore it, so refuse both
                sec_event("no_length", client_ip(scope), path)
                return await deny(send_with_headers, 411)
            if not length.isdigit() or len(length) > 9 or int(length) > max_body:
                sec_event("too_large", client_ip(scope), path)
                return await deny(send_with_headers, 413)
            bucket = path
        elif method == "GET" and path.startswith("/api/"):
            per_min, bucket = READ_PER_MIN, "/api/read"
        else:
            bucket = None
        if bucket and limited(ip := client_ip(scope), bucket, per_min):
            sec_event("rate_limited", ip, path)
            return await deny(send_with_headers, 429, [(b"retry-after", b"60")])
        await self.app(scope, receive, send_with_headers)


async def deny(send, status, headers=()):
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-length", b"0"), *headers]})
    await send({"type": "http.response.body", "body": b""})


async def auth(request: Request):
    if API_TOKEN and not hmac.compare_digest(request.headers.get("authorization", "").encode("latin-1"), f"Bearer {API_TOKEN}".encode()):
        ip = client_ip(request.scope)
        sec_event("unauthorized", ip, request.url.path)
        if limited(ip, "auth-fail", 30):  # token brute force: only failures count, so a correct client is never throttled
            raise HTTPException(429, "too many attempts", headers={"Retry-After": "60"})
        raise HTTPException(401, "unauthorized", headers={"WWW-Authenticate": "Bearer"})


app = FastAPI(title="Parsely Iran API", lifespan=lifespan, redoc_url=None,
              docs_url="/docs" if API_DOCS else None, openapi_url="/openapi.json" if API_DOCS else None)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(Guard)


def row(p, hist, last5, last30):
    return {"id": p["id"], "title_fa": p["title_fa"], "title_en": p["title_en"], "section": p["section"],
            "author_fa": p["author"][0], "author_en": p["author"][1], "published": p["published"],
            "readers": round(last5[p["id"]] / 300 * p["engaged"]), "views_30m": last30[p["id"]],
            "views_24h": sum(hist[-24:]), "spark": hist[-12:]}


MEMO = {}  # second -> serialized overview; the ticker only adds data every 2 s, so one build per second serves every viewer


@app.get("/api/overview", dependencies=[Depends(auth)])
async def overview():  # async on purpose: on the event loop nothing else mutates POSTS/BUCKETS mid-build, and no thread hop per request
    key = int(time.time())
    if key not in MEMO:
        MEMO.clear()
        MEMO[key] = json.dumps(build_overview(), ensure_ascii=False, separators=(",", ":")).encode()
    return Response(MEMO[key], media_type="application/json")


def build_overview():
    m = int(time.time() // 60)
    by_t = {b["t"]: b for b in BUCKETS}
    recent = [by_t[t] for t in range(m - 29, m + 1) if t in by_t]
    total = lambda key, bs: sum((b[key] for b in bs), Counter())
    last5, last30 = total("posts", recent[-5:]), total("posts", recent)
    refs, devs = total("refs", recent), total("devices", recent)
    hist = {pid: history(p, 48) for pid, p in POSTS.items()}
    series = [sum(h[i] for h in hist.values()) for i in range(48)]
    today, prev = sum(series[24:]), sum(series[:24])
    sections = Counter()
    for pid, h in hist.items():
        if POSTS[pid]["section"]:
            sections[POSTS[pid]["section"]] += sum(h[24:])
    engaged = sum(POSTS[pid]["engaged"] * sum(h[24:]) for pid, h in hist.items()) / max(today, 1)
    rows = [row(p, hist[p["id"]], last5, last30) for p in POSTS.values()]
    rows.sort(key=lambda r: (r["views_30m"], r["views_24h"]), reverse=True)
    return {
        "readers": sum(r["readers"] for r in rows), "pageviews": today, "visitors": round(today * 0.61),
        "change": round((today - prev) / max(prev, 1) * 100, 1), "engaged": round(engaged), "posts": len(POSTS),
        "series": series[24:], "prev_series": series[:24],
        "realtime": [by_t[t]["posts"].total() if t in by_t else 0 for t in range(m - 29, m + 1)],
        "referrers": [{"key": k, "value": refs[k]} for k in REFERRERS],
        "devices": [{"key": k, "value": devs[k]} for k in DEVICES],
        "sections": [{"key": k, "value": v} for k, v in sections.most_common()],
        "top": rows[:12],
    }


def deseason(hist, base_t):
    """Log views with the daily Tehran rhythm divided out; hist[-1] is the hour starting at base_t."""
    return [math.log(v / season(base_t - (len(hist) - 1 - i) * 3600) + 1) for i, v in enumerate(hist)]


def forecast(y, base_t, horizon=24):
    """Log-linear trend on the last 8 de-seasonalised hours, projected forward with a widening band."""
    y = y[-8:]
    if len(y) >= 3:
        slope, icpt = linear_regression(range(len(y)), y)
        resid = pstdev(v - (icpt + slope * i) for i, v in enumerate(y))
        level = icpt + slope * (len(y) - 1)
    else:
        slope, resid, level = 0.3, 0.3, y[-1]
    fc, lo, hi = [], [], []
    for i in range(1, horizon + 1):
        # ponytail: rising posts get a slope damped toward decay; swap for a fitted lifecycle model once real history exists
        slope = max(slope - 0.08, -0.5) if slope > -0.05 else slope
        level += slope
        band, s = min((resid + 0.05) * math.sqrt(i) * 0.8, 0.5), season(base_t + i * 3600)
        fc.append(round((math.exp(level) - 1) * s))
        lo.append(round(max(math.exp(level - band) - 1, 0) * s))
        hi.append(round((math.exp(level + band) - 1) * s))
    return fc, lo, hi


@app.get("/api/posts/{pid}", dependencies=[Depends(auth)])
async def post(pid: str):
    p = POSTS.get(pid)
    if not p:
        raise HTTPException(404, "post not found")
    now = time.time()
    hist = history(p, max(1, min(72, int((now - p["published"]) // 3600) + 1)))
    base_t = now // 3600 * 3600
    y = deseason(hist, base_t)
    trend = linear_regression(range(len(y[-8:])), y[-8:])[0] if len(y) >= 3 else 1
    fc, lo, hi = forecast(y, base_t)
    cur, peak = math.exp(y[-1]), math.exp(max(y))
    stage = "rising" if trend > 0.05 else "peak" if cur > 0.6 * peak else "decaying" if cur > 0.2 * peak else "evergreen"
    total = sum(hist)
    w = sum(p["refs"])
    recent = list(BUCKETS)
    r = row(p, hist, sum((b["posts"] for b in recent[-5:]), Counter()), sum((b["posts"] for b in recent), Counter()))
    return {**r, "history": hist, "forecast": fc, "low": lo, "high": hi, "total": total, "forecast_total": sum(fc),
            "stage": stage, "engaged": p["engaged"],
            "referrers": [{"key": k, "value": round(total * v / w)} for k, v in zip(REFERRERS, p["refs"])]}


class Event(BaseModel):
    url: str = Field(max_length=500)
    title: str = Field("", max_length=300)
    referrer: str = Field("", max_length=500)
    host: str = Field("", max_length=200, pattern=r"^[A-Za-z0-9.\-:]*[A-Za-z0-9][A-Za-z0-9.\-:]*$")  # needs one letter or digit: "." would match every referrer


def classify(ref, host):
    try:
        site = urlsplit(ref.lower()).hostname or ""  # hostname only: "netflix.com" must not read as x.com
    except ValueError:  # e.g. "http://[bad"
        return "direct"
    labels = site.split(".")
    base = ".".join(labels[-2:])  # registrable-ish domain: www.x.com -> x.com
    if "google" in labels:
        return "google"
    if "telegram" in labels or base == "t.me":
        return "telegram"
    if "instagram" in labels:
        return "instagram"
    if "twitter" in labels or base in ("x.com", "t.co"):
        return "x"
    me = host.lower().split(":")[0]
    return "internal" if me and (site == me or site.endswith("." + me)) else "direct"


@app.post("/api/track", status_code=204)
async def track(request: Request):
    try:
        e = Event.model_validate_json(await request.body())  # sendBeacon posts text/plain, so parse manually
    except ValidationError:
        return Response(status_code=400)
    pid = "t" + hashlib.md5(f"{e.host}{e.url}".encode(), usedforsecurity=False).hexdigest()[:8]
    if pid not in POSTS:
        if len(POSTS) >= MAX_POSTS:
            evict()
        POSTS[pid] = dict(id=pid, title_fa=e.title or e.url, title_en=e.title or e.url, section=None,
                          author=("—", "—"), published=time.time(), peak=0, tau=1, k=1, floor=0, engaged=60,
                          refs=[1] * len(REFERRERS))
    ua = request.headers.get("user-agent", "")
    dev = "tablet" if re.search(r"iPad|Tablet", ua) else "mobile" if "Mobile" in ua else "desktop"
    record(bucket(), pid, classify(e.referrer, e.host), dev)
    TRACKED[pid, int(time.time() // 3600)] += 1
    return Response(status_code=204)


TRACKER_JS = """(function(){var s=document.currentScript,e=new URL(s.src).origin+'/api/track';
function t(){navigator.sendBeacon(e,JSON.stringify({url:location.pathname,title:document.title,referrer:document.referrer,host:location.host}))}
t();addEventListener('popstate',t)})();"""


@app.get("/tracker.js")
async def tracker():
    return Response(TRACKER_JS, media_type="application/javascript", headers={"cache-control": "public, max-age=3600"})


# ---------- Persian / English NLP ----------
STOP = set("""و در به از که این را با است برای آن یک تا هم بر شد می شود کرد ها های نیز اما یا ما من تو او شما
آنها بود باشد دارد کند کرده شده خود هر چه نه اگر پس همه روی بین ولی چون درباره بسیار خیلی دیگر همین
آن‌ها می‌شود می‌کند هست نیست بودند کنند داریم دارند ای الان حتی فقط باید چرا کی کجا چطور چگونه آیا
the a an and or of to in on for is are was were be been it this that with as at by from not but have has had
you we they i he she my our your their so if very just can will would do does did""".split())
POS = set("""خوب عالی عالیه بهترین راضی سریع زیبا دوست ممنون مرسی خوشحال موفق رشد کیفیت لذت مفید جذاب آسان
راحت پیشنهاد ارزان حرفه‌ای شگفت‌انگیز محشر great good love excellent fast amazing happy easy best nice helpful""".split())
NEG = set("""بد ضعیف کند گران گرون مشکل خراب افتضاح ناراضی تاخیر تأخیر اشتباه بدترین سخت متاسفانه متأسفانه
کاهش شکایت قطع نامناسب پیچیده ناامید bad slow poor expensive broken worst hate problem terrible bug""".split())


def normalize(text):
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
    return re.sub(r"[ً-ٰٟـ]", "", text)  # diacritics + tatweel


def questions(text):
    """Sentences ending in ? or ؟. Split once and walk the pieces: the regex `[^.!؟?\\n]+[؟?]` is quadratic on unpunctuated text."""
    parts = re.split(r"([.!؟?\n]+)", text)  # text, delimiters, text, delimiters, ...
    return [t.strip() + d[0] for t, d in zip(parts[::2], parts[1::2]) if t.strip() and d[0] in "؟?"][:8]


def analyze(text):
    text = normalize(text)
    words = [w.strip("‌").lower() for w in re.findall(r"[\w‌]+", text) if not w.isdigit()]
    words = [w for w in words if w]
    content = [w for w in words if len(w) > 1 and w not in STOP]
    pos, neg = sum(w in POS for w in words), sum(w in NEG for w in words)
    sentences = [s.strip() for s in re.split(r"[.!؟?\n]+", text) if s.strip()]
    fa_chars = len(re.findall(r"[؀-ۿ]", text))
    return {
        "lang": "fa" if fa_chars >= len(re.findall(r"[A-Za-z]", text)) else "en",
        "words": len(words), "sentences": len(sentences), "reading_sec": round(len(words) / 200 * 60),
        "keywords": [{"term": t, "count": c} for t, c in Counter(content).most_common(12)],
        "sentiment": {"score": round((pos - neg) / max(pos + neg, 1), 2), "positive": pos, "negative": neg},
        "questions": questions(text),
    }


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.post("/api/nlp", dependencies=[Depends(auth)])
def nlp(body: Text):
    return analyze(body.text)


@app.get("/health")
async def health():
    return {"ok": True}
