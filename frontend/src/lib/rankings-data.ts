import { readFile } from "node:fs/promises";
import path from "node:path";
import { stripJk } from "@/lib/format";

export interface FurthestBelowHighRow {
  symbol: string;
  company_name: string;
  pct_below_high: number;
}

export interface LowestFreeFloatRow {
  symbol: string;
  company_name: string;
  free_float: number;
}

export interface McapChangeRow {
  symbol: string;
  company_name: string;
  yearly_mcap_change: number;
}

export interface DailyMoveRow {
  symbol: string;
  company_name: string;
  /** Ratio, e.g. 0.248 = +24.8%. Signed. */
  daily_close_change: number;
}

/** @deprecated kept for the existing Home teaser import - use FurthestBelowHighRow */
export type RankingRow = FurthestBelowHighRow;

export interface RankingsData {
  as_of: string;
  source_file: string;
  furthest_below_52w_high: FurthestBelowHighRow[];
  lowest_free_float: LowestFreeFloatRow[];
  mcap_change: {
    increases: McapChangeRow[];
    decreases: McapChangeRow[];
    evaluable_count: number;
  };
  /** Top 100 one-day moves by absolute size, up and down mixed. */
  biggest_daily_moves: DailyMoveRow[];
}

/**
 * Reads data/app/rankings.json, written by
 * pipeline/appdata/build_rankings.py. Server-only (fs): never import
 * from a "use client" component.
 */
export async function getRankingsData(): Promise<RankingsData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "rankings.json");
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as RankingsData;
  // Sectors symbols carry ".JK" internally; every table/link is user-facing,
  // so normalize once here rather than at each render site.
  const stripRow = <T extends { symbol: string }>(row: T): T => ({ ...row, symbol: stripJk(row.symbol) });
  return {
    ...parsed,
    furthest_below_52w_high: parsed.furthest_below_52w_high.map(stripRow),
    lowest_free_float: parsed.lowest_free_float.map(stripRow),
    mcap_change: {
      ...parsed.mcap_change,
      increases: parsed.mcap_change.increases.map(stripRow),
      decreases: parsed.mcap_change.decreases.map(stripRow),
    },
    biggest_daily_moves: (parsed.biggest_daily_moves ?? []).map(stripRow),
  };
}
