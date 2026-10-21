"""Self-check for the pure logic: cd backend && .venv/bin/python test_app.py"""
import time

from app import analyze, classify, deseason, forecast, questions

r = analyze("این محصول عالی است ولي ارسال خیلی کند بود. چرا پشتیبانی جواب نمی‌دهد؟ ارسال ارسال")
assert r["lang"] == "fa" and r["sentences"] == 3, r
assert r["keywords"][0] == {"term": "ارسال", "count": 3}, r["keywords"]
assert r["sentiment"] == {"score": 0.0, "positive": 1, "negative": 1}, r["sentiment"]
assert r["questions"] == ["چرا پشتیبانی جواب نمی‌دهد؟"], r["questions"]
assert analyze("Great app, love it")["sentiment"]["score"] == 1.0
assert questions("چرا؟ نه. why now? ok!! ?  x") == ["چرا؟", "why now?"]

for text in ("a" * 20000, "ab " * 6000, "؟" * 20000, "a?" * 10000, ("چرا " * 5000)):  # regex worst cases: must stay linear
    t0 = time.perf_counter()
    analyze(text)
    assert time.perf_counter() - t0 < 1.5, f"slow NLP input {text[:6]!r}"

base = time.time() // 3600 * 3600
fc, lo, hi = forecast(deseason([5000, 4000, 3200, 2600, 2100, 1700, 1400, 1100], base), base)
assert len(fc) == 24 and all(l <= f <= h for l, f, h in zip(lo, fc, hi))
assert fc[-1] < 1100, "decaying post must keep decaying"
fc, *_ = forecast(deseason([10], base), base)  # brand-new post: no crash, finite
assert all(v >= 0 for v in fc)

for ref, host, want in [
    ("https://www.google.com/", "site.ir", "google"), ("https://www.google.co.uk/x", "site.ir", "google"),
    ("https://t.me/news", "site.ir", "telegram"), ("https://www.x.com/a", "site.ir", "x"), ("https://t.co/abc", "site.ir", "x"),
    ("https://site.ir/a", "site.ir", "internal"), ("https://m.site.ir/", "site.ir", "internal"),
    ("http://localhost:3000/x", "localhost:3000", "internal"), ("", "site.ir", "direct"),
    ("https://netflix.com/", "site.ir", "direct"), ("https://box.com/", "site.ir", "direct"),  # substring "x.com" is not x.com
    ("https://evilsite.ir/", "site.ir", "direct"), ("http://[bad", "a.b", "direct"),  # lookalike host, malformed URL
]:
    assert classify(ref, host) == want, (ref, host, classify(ref, host), want)
print("ok")
