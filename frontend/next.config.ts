import type { NextConfig } from "next";

const backend = process.env.BACKEND_URL || "http://localhost:8737";

export default {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/tracker.js", destination: `${backend}/tracker.js` },
    ];
  },
} satisfies NextConfig;
