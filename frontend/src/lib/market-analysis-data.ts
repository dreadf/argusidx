import { readFile } from "node:fs/promises";
import path from "node:path";
import { stripJk } from "@/lib/format";

/**
 * Reads data/app/market_analysis.json, written by
 * pipeline/appdata/build_market_analysis.py: two Pasar readings for the
 * window since the IHSG peak, added alongside the existing Pasar sections.
 * Descriptive, one snapshot, not a trial (see the builder's docstring for
 * the constant-share-count assumption). Server-only (fs).
 */

export interface MarketAnalysisIndexRow {
  code: string;
  label: string;
  change_since_peak: number;
  change_1y: number;
}

export interface MarketAnalysisDragRow {
  symbol: string;
  company_name: string;
  return: number;
  value_change: number;
  /** Null when the total market value did not fall (fall = 0): share of a fall makes no sense then. */
  drag_share: number | null;
}

export interface MarketAnalysisUpRow {
  symbol: string;
  company_name: string;
  return: number;
}

export interface MarketAnalysisData {
  as_of: string;
  source_files: string[];
  peak_window: { start: string; end: string };
  indices: MarketAnalysisIndexRow[];
  universe: { n: number; market_value_start: number; market_value_end: number; median_return: number; down: number };
  /** Null when the total market value did not fall: "five stocks bear the fall" has no fall to bear. */
  top5_drag_share: number | null;
  drag: MarketAnalysisDragRow[];
  large_caps: { n: number; n_up: number; n_producer: number; median_return: number; up: MarketAnalysisUpRow[] };
}

interface RawFile extends Omit<MarketAnalysisData, "drag" | "large_caps"> {
  drag: MarketAnalysisDragRow[];
  large_caps: MarketAnalysisData["large_caps"];
}

let cache: MarketAnalysisData | null = null;

export async function getMarketAnalysisData(): Promise<MarketAnalysisData> {
  if (cache) return cache;
  const filePath = path.join(process.cwd(), "..", "data", "app", "market_analysis.json");
  const raw = JSON.parse(await readFile(filePath, "utf-8")) as RawFile;
  cache = {
    ...raw,
    drag: raw.drag.map((r) => ({ ...r, symbol: stripJk(r.symbol) })),
    large_caps: { ...raw.large_caps, up: raw.large_caps.up.map((r) => ({ ...r, symbol: stripJk(r.symbol) })) },
  };
  return cache;
}
