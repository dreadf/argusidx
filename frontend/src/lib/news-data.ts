import { readFile } from "node:fs/promises";
import path from "node:path";
import { stripJk } from "@/lib/format";

export interface NewsCoverageRow {
  symbol: string;
  company_name: string | null;
  bullish: number;
  bearish: number;
  mentions: number;
}

export interface NewsSentimentData {
  as_of: string;
  first_date: string;
  last_date: string;
  note: string;
  n_articles: number;
  bullish_articles_pct: number;
  n_mentions: number;
  bullish_mentions_pct: number;
  n_symbols: number;
  multi_symbol_articles: number;
  most_covered: NewsCoverageRow[];
  /** Bare ticker -> counts (".JK" stripped once, here). */
  by_symbol: Record<string, { bullish: number; bearish: number }>;
}

/**
 * Reads data/app/news_sentiment.json, written by
 * pipeline/appdata/build_news_sentiment.py. Server-only (fs). The
 * Bullish/Bearish tags come from Sectors, not from ArgusIDX: anywhere this
 * is shown, say so, and always put a stock's split next to the market-wide
 * split (`bullish_mentions_pct`) rather than showing it bare.
 */
async function load_getNewsSentiment(): Promise<NewsSentimentData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "news_sentiment.json");
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as NewsSentimentData;
  return {
    ...parsed,
    most_covered: parsed.most_covered.map((r) => ({ ...r, symbol: stripJk(r.symbol) })),
    by_symbol: Object.fromEntries(Object.entries(parsed.by_symbol).map(([k, v]) => [stripJk(k), v])),
  };
}

let cached_getNewsSentiment: NewsSentimentData | null = null;

/** Parsed once per build/process: the stock page calls this for each of 962 pages, and re-reading the file each time exhausted memory during static generation. */
export async function getNewsSentiment(): Promise<NewsSentimentData> {
  if (cached_getNewsSentiment === null) cached_getNewsSentiment = await load_getNewsSentiment();
  return cached_getNewsSentiment;
}
