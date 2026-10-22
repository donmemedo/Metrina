import type { NextConfig } from "next";

const backend = process.env.BACKEND_URL || "http://localhost:8737";

// The Content-Security-Policy needs a per-request nonce, so proxy.ts sets it. Everything static lives here.
const headers = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

export default {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers }];
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/tracker.js", destination: `${backend}/tracker.js` },
    ];
  },
} satisfies NextConfig;
