import { readFile } from "node:fs/promises";
import path from "node:path";

export interface IdxTotalPoint {
  date: string;
  value: number;
}

export interface IdxTotalData {
  as_of: string;
  source_file: string;
  series: IdxTotalPoint[];
  latest: IdxTotalPoint | null;
  min: IdxTotalPoint | null;
  max: IdxTotalPoint | null;
}

/**
 * Reads data/app/idx_total.json, written by
 * pipeline/appdata/build_idx_total.py. Server-only (fs): never import
 * from a "use client" component.
 */
export async function getIdxTotalData(): Promise<IdxTotalData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "idx_total.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as IdxTotalData;
}
