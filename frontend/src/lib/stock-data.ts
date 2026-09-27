import { readFile } from "node:fs/promises";
import path from "node:path";

export interface StockSnapshot {
  symbol: string;
  company_name: string;
  sector: string | null;
  sub_sector: string | null;
  industry: string | null;
  sub_industry: string | null;
  market_cap: number | null;
  market_cap_rank: number | null;
  free_float: number | null;
  last_close_price: number | null;
  "52_w_low_price": number | null;
  "52_w_high_price": number | null;
  position_in_52w_range: number | null;
  listing_date: string | null;
  listing_board: string | null;
}

export interface PeerComparison {
  level: string;
  group: string;
  peer_count: number;
  metric: string;
  own_value: number | null;
  better_than_count: number | null;
  comparable_count: number | null;
}

export interface TrippedFlag {
  key: string;
  label: string;
  detail: Record<string, unknown>;
}

export interface SuspensionEvent {
  date: string;
  reason: string;
  pdf_url: string;
  category: string;
  category_label_id: string;
  group: string;
  group_label_id: string;
}

export interface SuspensionHistory {
  events: SuspensionEvent[];
  count: number;
  universe_count: number;
  companies_with_suspensions: number;
  base_rate_pct: number;
  more_than_pct: number;
}

export interface BankingRatio {
  value: number;
  better_than_count: number;
  comparable_count: number;
}

export interface LensBanking {
  company_name: string;
  loan_to_deposit_ratio: number | null;
  loan_growth: number | null;
  ratios: {
    "casa_ratio[2025]": BankingRatio | null;
    "capital_adequacy_ratio[2025]": BankingRatio | null;
    "net_interest_margin[2025]": BankingRatio | null;
    npl_ratio: BankingRatio | null;
  };
}

export interface CommodityTrend {
  commodity: string;
  latest_date: string;
  year_ago_date: string | null;
  change_12m_pct: number | null;
  range_start: string;
  position_in_range: number | null;
}

export interface LensExtractive {
  company_type: string | null;
  key_operation: string | null;
  commodity_type: string[];
  commodity_trends: CommodityTrend[];
}

export interface BeatGoldResult {
  company_name: string | null;
  years: number;
  beat_index: boolean | null;
  beat_gold: boolean | null;
  beat_deposit: boolean | null;
  beat_typical_stock: boolean;
  beat_sector_peer: boolean | null;
}

export type H1FindingState = "risky_side" | "calm_side" | "in_between" | "weaker_evidence_for_size_range";

export interface H1Finding {
  state: H1FindingState;
  size_bucket: "smallest" | "small_mid" | "mid_large" | "largest";
  free_float_tercile: "low" | "mid" | "high";
}

export interface InsiderActivity {
  buy_count: number;
  sell_count: number;
  last_transaction_date: string | null;
  net_direction: "net_buying" | "net_selling" | "balanced";
}

export interface SectorContext {
  sector: string;
  own_roe_pct: number | null;
  own_pe: number | null;
  sector_typical_roe_pct: number | null;
  sector_roe_n: number;
  sector_typical_pe: number | null;
  sector_pe_n: number;
  sector_company_count: number;
}

export interface CorporateActions {
  as_of: string;
  window_start: string;
  window_end: string;
  dividends: {
    ex_date: string;
    payment_date: string | null;
    amount: number | null;
    implied_yield: number | null;
  }[];
  agms: { agm_date: string; agm_time: string | null; cancelled: boolean }[];
  rights_issues: {
    ex_date: string;
    price: number | null;
    old_ratio: number | null;
    new_ratio: number | null;
    trading_period_start: string | null;
    trading_period_end: string | null;
  }[];
  stock_splits: { date: string; ratio: string | null }[];
}

export interface StockPageData {
  snapshot: StockSnapshot;
  peer_comparison: PeerComparison | null;
  sector_context: SectorContext | null;
  flags: TrippedFlag[];
  suspension_history: SuspensionHistory | null;
  lens_banking: LensBanking | null;
  lens_extractive: LensExtractive | null;
  beat_gold: BeatGoldResult | null;
  h1_finding: H1Finding | null;
  insider_activity: InsiderActivity | null;
  corporate_actions: CorporateActions;
}

interface StocksFile {
  as_of: string;
  source_file: string;
  stocks: Record<string, StockPageData>;
}

let cache: StocksFile | null = null;

async function loadStocksFile(): Promise<StocksFile> {
  if (cache) return cache;
  const filePath = path.join(process.cwd(), "..", "data", "app", "stocks.json");
  const raw = await readFile(filePath, "utf-8");
  cache = JSON.parse(raw) as StocksFile;
  return cache;
}

/**
 * Reads data/app/stocks.json, written by
 * pipeline/appdata/build_stock_pages.py. Server-only (fs): never import
 * from a "use client" component. `code` is the bare ticker (e.g. "BBCA");
 * the sweep's own symbol format ("BBCA.JK") is an implementation detail.
 */
export async function getStockData(code: string): Promise<StockPageData | null> {
  const file = await loadStocksFile();
  return file.stocks[`${code.toUpperCase()}.JK`] ?? null;
}

export async function getAllStockCodes(): Promise<string[]> {
  const file = await loadStocksFile();
  return Object.keys(file.stocks).map((symbol) => symbol.replace(/\.JK$/, ""));
}

export async function getStocksAsOf(): Promise<string> {
  const file = await loadStocksFile();
  return file.as_of;
}

export interface SearchEntry {
  code: string;
  name: string;
}

/** SearchEntry plus the numbers needed to show "-27,7% dari tertinggi"
 * beside a stock in a list (search results, watchlist) without loading
 * its full page. Only /cari and /watchlist load this: it is ~4x the
 * size of the plain index, too heavy to ship on every page. */
export interface QuoteEntry extends SearchEntry {
  sector: string | null;
  price: number | null;
  low: number | null;
  high: number | null;
}

/**
 * Flat {code, name} index for every stock, used by the site-wide search
 * box (components/stock-search.tsx). Derived from the already-cached
 * stocks.json rather than a separate build artifact: no new pipeline
 * output needed for a projection this small (~40KB) of data already
 * loaded into memory by every other function in this module.
 */
export async function getSearchIndex(): Promise<SearchEntry[]> {
  const file = await loadStocksFile();
  return Object.entries(file.stocks).map(([symbol, data]) => ({
    code: symbol.replace(/\.JK$/, ""),
    name: data.snapshot.company_name,
  }));
}

export async function getQuoteIndex(): Promise<QuoteEntry[]> {
  const file = await loadStocksFile();
  return Object.entries(file.stocks).map(([symbol, data]) => ({
    code: symbol.replace(/\.JK$/, ""),
    name: data.snapshot.company_name,
    sector: data.snapshot.sector,
    price: data.snapshot.last_close_price,
    low: data.snapshot["52_w_low_price"],
    high: data.snapshot["52_w_high_price"],
  }));
}

export interface SectorStockRow {
  code: string;
  name: string;
  marketCap: number | null;
  marketCapRank: number | null;
  price: number | null;
  low: number | null;
  high: number | null;
  /** Number of the four anomaly flags this stock trips. */
  flagCount: number;
}

/** Every stock in one sector (Sectors' English key), largest market value first. */
export async function getSectorStocks(sectorKey: string): Promise<SectorStockRow[]> {
  const file = await loadStocksFile();
  return Object.entries(file.stocks)
    .filter(([, d]) => d.snapshot.sector === sectorKey)
    .map(([symbol, d]) => ({
      code: symbol.replace(/\.JK$/, ""),
      name: d.snapshot.company_name,
      marketCap: d.snapshot.market_cap,
      marketCapRank: d.snapshot.market_cap_rank,
      price: d.snapshot.last_close_price,
      low: d.snapshot["52_w_low_price"],
      high: d.snapshot["52_w_high_price"],
      flagCount: d.flags.length,
    }))
    .sort((a, b) => (b.marketCap ?? -1) - (a.marketCap ?? -1) || a.code.localeCompare(b.code));
}
