"""Edge-hardening tests, in-process (no server needed): cd backend && .venv/bin/python test_edge.py"""
import asyncio, inspect, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__) or ".")
import app as A
from fastapi.testclient import TestClient

res = []
def check(name, ok, detail=""):
    res.append(ok); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

ev = lambda url, host="site.ir", ref="": json.dumps({"url": url, "title": "t", "referrer": ref, "host": host})
TXT = {"content-type": "text/plain"}


def guard(method, path, headers, ip="1.2.3.4"):
    """Drive the Guard middleware directly with a raw ASGI scope (a normal HTTP client can't send hostile framing)."""
    out = []
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})
    async def send(m): out.append(m)
    scope = {"type": "http", "method": method, "path": path, "scheme": "http", "client": (ip, 1),
             "headers": [(k.encode(), v.encode()) for k, v in headers]}
    asyncio.run(A.Guard(app)(scope, None, send))
    return out[0]["status"], dict(out[0]["headers"])


with TestClient(A.app) as c:
    # --- baseline headers, hidden docs, compression ---
    r = c.get("/health")
    check("health 200 + nosniff/XFO/CSP/Permissions headers", r.status_code == 200 and r.headers.get("x-content-type-options") == "nosniff"
          and r.headers.get("x-frame-options") == "DENY" and "frame-ancestors" in r.headers.get("content-security-policy", "")
          and "permissions-policy" in r.headers)
    check("/docs, /redoc, /openapi.json hidden", all(c.get(p).status_code == 404 for p in ("/docs", "/redoc", "/openapi.json")))
    r = c.get("/api/overview", headers={"accept-encoding": "gzip"})
    check("overview 200 gzip json", r.status_code == 200 and r.headers.get("content-encoding") == "gzip" and r.headers["content-type"].startswith("application/json"))
    check("post p1 200 / unknown 404", c.get("/api/posts/p1").status_code == 200 and c.get("/api/posts/nope").status_code == 404)
    check("no CORS headers on read API", "access-control-allow-origin" not in c.get("/api/overview", headers={"origin": "https://evil.example"}).headers)

    # --- shared state is only touched on the event loop (a sync handler would run on a thread and could race again) ---
    check("handlers that touch shared state are async", all(inspect.iscoroutinefunction(f) for f in (A.overview, A.post, A.track, A.auth)))
    check("no threading.Lock left in app", "threading" not in open(A.__file__).read())

    # --- performance: the memo must beat a rebuild (relative, so a loaded machine does not flake) ---
    def best(fn, n=7):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
        return min(ts)
    t_build = best(A.build_overview)
    asyncio.run(A.overview())
    t_hit = best(lambda: asyncio.run(A.overview()))
    check("overview memo hit is >=3x cheaper than a rebuild", t_hit * 3 < t_build, f"build {t_build*1e3:.2f} ms, hit {t_hit*1e3:.3f} ms")

    # --- beacon intake ---
    check("track text/plain 204", c.post("/api/track", content=ev("/a"), headers=TXT).status_code == 204)
    check("track bad json -> 400", c.post("/api/track", content="{not json", headers=TXT).status_code == 400)
    check("track oversized -> 413 with security headers", (lambda r: r.status_code == 413 and r.headers.get("x-content-type-options") == "nosniff")(c.post("/api/track", content="x" * 5000)))
    check("host '.', '..', '-' rejected", all(c.post("/api/track", content=ev("/h", host=h), headers=TXT).status_code == 400 for h in (".", "..", "-", "")))
    check("hosts site.ir, localhost:3000, 127.0.0.1 accepted", all(c.post("/api/track", content=ev("/h", host=h), headers=TXT).status_code == 204 for h in ("site.ir", "localhost:3000", "127.0.0.1")))

    # --- raw framing: Content-Length / Transfer-Encoding games ---
    s = lambda h: guard("POST", "/api/track", h)[0]
    check("chunked + small Content-Length -> 411 (cap bypass)", s([("content-length", "10"), ("transfer-encoding", "chunked")]) == 411)
    check("chunked without Content-Length -> 411", s([("transfer-encoding", "chunked")]) == 411)
    check("no length -> 411", s([]) == 411)
    check("5000-digit Content-Length -> 413, no crash", s([("content-length", "9" * 5000)]) == 413)
    check("negative / non-numeric Content-Length -> 413", s([("content-length", "-5")]) == 413 and s([("content-length", "1e3")]) == 413)
    check("exact cap passes, cap+1 refused", s([("content-length", "4096")]) == 200 and s([("content-length", "4097")]) == 413)

    # --- rate limiting and client identity ---
    check("client_ip ignores X-Forwarded-For unless TRUST_PROXY", A.client_ip({"headers": [(b"x-forwarded-for", b"6.6.6.6")], "client": ("9.9.9.9", 1)}) == "9.9.9.9")
    A.TRUST_PROXY = True
    sc = lambda *v: {"headers": [(b"x-forwarded-for", x.encode()) for x in v], "client": ("9.9.9.9", 1)}
    check("client_ip takes the LAST forwarded entry", A.client_ip(sc("6.6.6.6, 5.5.5.5, 1.2.3.4")) == "1.2.3.4")
    check("client_ip: last header wins, empty falls back to peer, length capped",
          A.client_ip(sc("6.6.6.6", "1.2.3.4")) == "1.2.3.4" and A.client_ip(sc("")) == "9.9.9.9" and len(A.client_ip(sc("a" * 5000))) == 64)
    A.HITS.clear()
    codes = [c.post("/api/track", content=ev(f"/xff{i}"), headers={**TXT, "x-forwarded-for": f"10.0.{i // 250}.{i % 250}, 198.51.100.7"}).status_code for i in range(130)]
    check("forging the left of X-Forwarded-For does not dodge the limit", 429 in codes, f"first 429 at #{codes.index(429) if 429 in codes else -1}")
    r = c.post("/api/track", content=ev("/e"), headers={**TXT, "x-forwarded-for": "203.0.113.9"})
    check("a different real client keeps its own budget", r.status_code == 204)
    A.TRUST_PROXY = False
    A.HITS.clear()
    codes = [c.post("/api/track", content=ev(f"/rl{i}"), headers=TXT).status_code for i in range(130)]
    check("rate limit -> 429 with Retry-After", 429 in codes)
    A.HITS.clear(); A.READ_PER_MIN, keep = 5, A.READ_PER_MIN
    codes = [c.get("/api/overview").status_code for _ in range(8)]
    check("read endpoints are rate limited too", codes[:5] == [200] * 5 and 429 in codes[5:], str(codes))
    A.READ_PER_MIN = keep; A.HITS.clear()

    # --- state caps ---
    A.LIMITS["/api/track"] = (4096, 10**6)
    for i in range(700):
        c.post("/api/track", content=ev(f"/junk{i}"), headers=TXT)
    check("POSTS capped at MAX_POSTS via eviction", len(A.POSTS) <= A.MAX_POSTS, len(A.POSTS))
    check("seeded posts survive eviction", all(f"p{i}" in A.POSTS for i in range(1, 25)))
    check("overview + post still fine after flood", c.get("/api/overview").status_code == 200 and c.get("/api/posts/p1").status_code == 200)
    A.LIMITS["/api/track"] = (4096, 120); A.HITS.clear()
    check("tracker.js cacheable", "max-age=3600" in c.get("/tracker.js").headers.get("cache-control", ""))

    # --- optional bearer token ---
    A.API_TOKEN = "s3cret"; A.HITS.clear()
    check("token set -> 401 without bearer, 200 with", c.get("/api/overview").status_code == 401
          and c.get("/api/overview", headers={"authorization": "Bearer s3cret"}).status_code == 200)
    r = c.get("/api/overview", headers={"authorization": b"Bearer \xe9\xff"})
    check("non-ASCII Authorization header -> 401, not a 500", r.status_code == 401, r.status_code)
    A.HITS.clear()
    codes = [c.get("/api/overview", headers={"authorization": f"Bearer guess{i}"}).status_code for i in range(40)]
    check("token brute force -> 429 after 30 failures", codes[:30] == [401] * 30 and codes[30] == 429, f"{codes[29]},{codes[30]}")
    check("the right token still works while the failure bucket is full", c.get("/api/overview", headers={"authorization": "Bearer s3cret"}).status_code == 200)
    A.API_TOKEN = ""; A.HITS.clear()
    check("security events are counted", A.EVENTS["too_large"] >= 1 and A.EVENTS["rate_limited"] >= 1 and A.EVENTS["unauthorized"] >= 1, dict(A.EVENTS))

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
