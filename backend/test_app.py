"""Self-check: python test_app.py"""
import time

from app import analyze, deseason, forecast, classify

r = analyze("این محصول عالی است ولي ارسال خیلی کند بود. چرا پشتیبانی جواب نمی‌دهد؟ ارسال ارسال")
assert r["lang"] == "fa" and r["sentences"] == 3, r
assert r["keywords"][0] == {"term": "ارسال", "count": 3}, r["keywords"]
assert r["sentiment"] == {"score": 0.0, "positive": 1, "negative": 1}, r["sentiment"]
assert r["questions"] == ["چرا پشتیبانی جواب نمی‌دهد؟"], r["questions"]
assert analyze("Great app, love it")["sentiment"]["score"] == 1.0

base = time.time() // 3600 * 3600
fc, lo, hi = forecast(deseason([5000, 4000, 3200, 2600, 2100, 1700, 1400, 1100], base), base)
assert len(fc) == 24 and all(l <= f <= h for l, f, h in zip(lo, fc, hi))
assert fc[-1] < 1100, "decaying post must keep decaying"
fc, *_ = forecast(deseason([10], base), base)  # brand-new post: no crash, finite
assert all(v >= 0 for v in fc)

assert classify("https://www.google.com/", "site.ir") == "google"
assert classify("https://t.me/news", "site.ir") == "telegram"
assert classify("https://site.ir/a", "site.ir") == "internal"
assert classify("", "site.ir") == "direct"
print("ok")
