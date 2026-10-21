import { NextResponse, type NextRequest } from "next/server";

const dev = process.env.NODE_ENV === "development";
const TOKEN = process.env.API_TOKEN; // server-side only, never NEXT_PUBLIC_*: it is added to proxied API calls, not to pages

/** Pages get a fresh CSP nonce; /api/* gets the bearer token (when one is configured) before the rewrite to the backend. */
export function proxy(req: NextRequest) {
  const headers = new Headers(req.headers);

  if (req.nextUrl.pathname.startsWith("/api/")) {
    headers.delete("authorization"); // never forward what the browser sent
    if (TOKEN) headers.set("authorization", `Bearer ${TOKEN}`);
    return NextResponse.next({ request: { headers } });
  }

  const nonce = btoa(crypto.randomUUID());
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'nonce-${nonce}'`,
    "style-src-attr 'unsafe-inline'", // React style={} attributes (chart geometry, colours); nonces cannot cover attributes
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${dev ? " ws:" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  headers.set("x-nonce", nonce);
  headers.set("content-security-policy", csp);
  const res = NextResponse.next({ request: { headers } });
  res.headers.set("content-security-policy", csp);
  return res;
}

export const config = {
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico|icon.svg|tracker.js).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
