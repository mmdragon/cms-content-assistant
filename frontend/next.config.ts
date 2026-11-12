import type { NextConfig } from "next";

// The browser only ever talks to this Next.js server. Requests to /api/* are
// proxied to the FastAPI backend, so the backend URL stays server-side and no
// secrets or cross-origin calls are needed in the client bundle.
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
