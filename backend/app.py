"""Parsely Iran — content analytics API: live event collector, lifecycle forecast, Persian NLP."""
import asyncio
import hashlib
import math
import random
import re
import time
from collections import Counter, deque
from contextlib import asynccontextmanager
from statistics import linear_regression, pstdev

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

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
    rnd, posts = random.Random(7), {}
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


def model(p, age_h):
    """Lifecycle curve: gamma-shaped rise, peak at tau hours, then decay onto an evergreen floor."""
    if age_h <= 0 or not p["peak"]:
        return 0.0
    x = age_h / p["tau"]
    return p["peak"] * (x ** p["k"] * math.exp(p["k"] * (1 - x)) + p["floor"])


def season(t):
    h = (t / 3600 + 3.5) % 24  # Tehran local hour
    return 0.25 + 0.75 * max(0.0, math.sin(math.pi * (h - 6) / 18))


def history(p, hours):
    base = time.time() // 3600 * 3600
    out = []
    for i in range(hours - 1, -1, -1):
        t = base - i * 3600
        noise = random.Random(f"{p['id']}:{int(t // 3600)}").uniform(0.85, 1.15)
        out.append(round(model(p, (t - p["published"]) / 3600) * season(t) * noise) + TRACKED[p["id"], int(t // 3600)])
    return out


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
        for _ in range(int(rate) + (random.random() < rate % 1)):
            record(b, p["id"], random.choices(REFERRERS, p["refs"])[0], random.choices(DEVICES, (62, 33, 5))[0])


async def ticker():
    while True:
        simulate(2, bucket())
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(_):
    m = int(time.time() // 60)
    for t in range(m - 29, m):
        simulate(60, new_bucket(t), t * 60)
    task = asyncio.create_task(ticker())
    yield
    task.cancel()


app = FastAPI(title="Parsely Iran API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def row(p, hist, last5, last30):
    return {"id": p["id"], "title_fa": p["title_fa"], "title_en": p["title_en"], "section": p["section"],
            "author_fa": p["author"][0], "author_en": p["author"][1], "published": p["published"],
            "readers": round(last5[p["id"]] / 300 * p["engaged"]), "views_30m": last30[p["id"]],
            "views_24h": sum(hist[-24:]), "spark": hist[-12:]}


@app.get("/api/overview")
def overview():
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


@app.get("/api/posts/{pid}")
def post(pid: str):
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
    host: str = Field("", max_length=200)


def classify(ref, host):
    ref = ref.lower()
    for key, marks in (("google", ("google.",)), ("telegram", ("t.me", "telegram")), ("instagram", ("instagram",)),
                       ("x", ("x.com", "twitter", "t.co/"))):
        if any(mk in ref for mk in marks):
            return key
    return "internal" if host and host in ref else "direct"


@app.post("/api/track", status_code=204)
async def track(request: Request):
    e = Event.model_validate_json(await request.body())  # sendBeacon posts text/plain, so parse manually
    pid = "t" + hashlib.md5(f"{e.host}{e.url}".encode()).hexdigest()[:8]
    if pid not in POSTS:
        if len(POSTS) > 500:  # cap memory against junk traffic
            return Response(status_code=204)
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
def tracker():
    return Response(TRACKER_JS, media_type="application/javascript")


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
    return re.sub(r"[ً-ٰٟـ]", "", text)  # diacritics + tatweel


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
        "questions": [q.strip() for q in re.findall(r"[^.!؟?\n]+[؟?]", text)][:8],
    }


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.post("/api/nlp")
def nlp(body: Text):
    return analyze(body.text)


@app.get("/health")
def health():
    return {"ok": True}
