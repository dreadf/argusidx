import { readFile } from "node:fs/promises";
import path from "node:path";

export interface SectorBreadth {
  near_high: number;
  middle: number;
  near_low: number;
  excluded: number;
  total_evaluable: number;
}

export interface SectorRow {
  sector: string;
  company_count: number;
  breadth: SectorBreadth;
  typical_roe_pct: number | null;
  roe_n: number;
  typical_pe: number | null;
  pe_n: number;
}

export interface SectorBreakdownData {
  as_of: string;
  source_file: string;
  /** Ordered by company_count, descending: never by a performance
   * metric. Sorting sectors by how well they're doing would itself be
   * a cross-sector ranking, which nothing else in this product does. */
  sectors: SectorRow[];
}

/**
 * Reads data/app/sector_breakdown.json, written by
 * pipeline/appdata/build_sector_breakdown.py. Server-only (fs): never
 * import from a "use client" component.
 */
export async function getSectorBreakdownData(): Promise<SectorBreakdownData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "sector_breakdown.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as SectorBreakdownData;
}
