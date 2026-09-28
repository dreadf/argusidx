import { NextResponse } from "next/server";
import { getStockData } from "@/lib/stock-data";
import { watchItems } from "@/lib/stock-read";
import { getReadInput } from "@/lib/stock-read-data";
import { buildFingerprint, describeChanges, isFingerprint, type StockFingerprint } from "@/lib/watchlist-changes";

/**
 * "Ada yang berubah" for the watched stocks named in the request. No
 * accounts and no server-side state (docs/PRODUCT.md §11): the browser
 * sends back the last fingerprint it saw per symbol (or null, first time),
 * and this recomputes each symbol's current one from data/app - already
 * loaded local files, 0 Sectors credits, nothing billed or persisted here.
 */

const MAX_SYMBOLS = 200;
// Matches api/ask/route.ts's carriedStock convention: every real ticker in stocks.json is exactly 4 characters.
const CODE_RE = /^[A-Z0-9]{4}$/;

interface Body {
  symbols?: unknown;
  seen?: unknown;
}

export async function POST(request: Request) {
  let body: Body;
  try {
    body = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ error: "JSON tidak valid." }, { status: 400 });
  }

  const symbolsRaw = body.symbols;
  if (!Array.isArray(symbolsRaw) || symbolsRaw.length === 0) {
    return NextResponse.json({ error: "symbols kosong." }, { status: 400 });
  }
  const symbols = [...new Set(symbolsRaw)].filter((s): s is string => typeof s === "string" && CODE_RE.test(s)).slice(0, MAX_SYMBOLS);
  if (symbols.length === 0) {
    return NextResponse.json({ error: "Tidak ada kode saham yang valid." }, { status: 400 });
  }
  const seenBody = typeof body.seen === "object" && body.seen !== null ? (body.seen as Record<string, unknown>) : {};

  const entries = await Promise.all(
    symbols.map(async (symbol) => {
      const data = await getStockData(symbol);
      if (!data) return null;
      const r = await getReadInput(symbol, data);
      if (!r) return null;
      const watch = watchItems(r);
      const current = buildFingerprint(data, watch);
      const titles = Object.fromEntries(watch.map((w) => [w.kind, w.title]));
      const seen = seenBody[symbol];
      const changes = describeChanges(isFingerprint(seen) ? seen : null, current, titles);
      return [symbol, { current, changes }] as const;
    })
  );

  const results = Object.fromEntries(entries.filter((e): e is readonly [string, { current: StockFingerprint; changes: string[] }] => e !== null));
  return NextResponse.json({ results });
}
