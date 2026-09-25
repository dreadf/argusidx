import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server routes (/api/ask and every page that reads searchParams) load
  // ../data/app/*.json at request time. That folder sits outside frontend/,
  // and the paths are built at runtime, so Next's file tracer never sees
  // them: verified 2026-09-20, the .nft.json trace for /api/ask listed zero
  // data/app files. A serverless deploy would then fail on the first
  // request. Trace from the repo root and include the folder explicitly.
  outputFileTracingRoot: path.join(__dirname, ".."),
  outputFileTracingIncludes: {
    "/*": ["../data/app/**/*"],
  },
  // Peringkat, Sektor and Tanda became tabs under Jelajah. The old URLs
  // stay valid so existing links, the README and scripts/preflight.sh keep
  // working.
  async redirects() {
    return [
      { source: "/peringkat", destination: "/jelajah", permanent: true },
      { source: "/sektor", destination: "/jelajah/sektor", permanent: true },
      { source: "/tanda", destination: "/jelajah/tanda", permanent: true },
    ];
  },
};

export default nextConfig;
