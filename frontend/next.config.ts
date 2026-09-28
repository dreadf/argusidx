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
    "/*": ["../data/app/**/*", "../docs/credit_ledger.md"],
  },
  // Jelajah became Pasar (2026-09-28): Peringkat and Deteksi anomali (now
  // "Tanda") moved to tabs under Temuan, sector pages under Pasar. Every old
  // URL stays valid so existing links, the README and scripts/preflight.sh
  // keep working. /jelajah itself is a page (app/jelajah/page.tsx) because
  // its ?urut=<measure> links need a lookup.
  async redirects() {
    return [
      { source: "/peringkat", destination: "/temuan/peringkat", permanent: true },
      { source: "/sektor", destination: "/pasar", permanent: true },
      { source: "/tanda", destination: "/temuan/tanda", permanent: true },
      { source: "/jelajah/pasar", destination: "/pasar", permanent: true },
      { source: "/jelajah/sektor", destination: "/pasar", permanent: true },
      { source: "/jelajah/sektor/:slug*", destination: "/pasar/sektor/:slug*", permanent: true },
      { source: "/jelajah/peringkat/:slug", destination: "/temuan/peringkat/:slug", permanent: true },
      { source: "/jelajah/anomali", destination: "/temuan/tanda", permanent: true },
      { source: "/jelajah/anomali/:jenis", destination: "/temuan/tanda/:jenis", permanent: true },
      { source: "/jelajah/tanda", has: [{ type: "query", key: "jenis", value: "(?<jenis>.+)" }], destination: "/temuan/tanda/:jenis", permanent: true },
      { source: "/jelajah/tanda", destination: "/temuan/tanda", permanent: true },
      // The stock page's reason pages became chips on the page itself
      // (2026-09-28); a reason opens as #alasan-<key> there.
      { source: "/saham/:kode/alasan", destination: "/saham/:kode", permanent: true },
      { source: "/saham/:kode/alasan/rekomendasi", destination: "/saham/:kode#alasan-tip", permanent: true },
      { source: "/saham/:kode/alasan/:alasan(turun|murah)", destination: "/saham/:kode#alasan-:alasan", permanent: true },
    ];
  },
};

export default nextConfig;
