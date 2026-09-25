import { readFile } from "node:fs/promises";
import path from "node:path";

export interface BoardStats {
  n: number;
  negative_rate_pct: number;
  mean_return_pct: number;
  median_return_pct: number;
}

export interface WelchT {
  t: number;
  diff_pct: number;
}

export interface HorizonResult {
  by_board: Record<string, BoardStats>;
  acceleration_vs_main_welch_t: WelchT | null;
}

export interface IpoBoardsPhase {
  n: number;
  horizons: Record<string, HorizonResult>;
}

export interface IpoBoardsData {
  as_of: string;
  note: string;
  tested_boards: string[];
  explore: IpoBoardsPhase;
  holdout: IpoBoardsPhase;
}

/**
 * Reads data/app/ipo_boards.json, written by
 * pipeline/appdata/build_ipo_boards.py (H13). Server-only (fs): never
 * import from a "use client" component.
 *
 * Unlike base-rates-data.ts's three results, this IS a pre-registered,
 * falsifiable hypothesis (counted in the project's trial counter):
 * falsified on the formal Welch-t test at every horizon, in both phases,
 * despite a large consistent negative-rate/median gap in the same
 * direction throughout. Render BOTH halves of that story wherever this
 * is shown: never present only the favorable frequency framing.
 * `note` carries the full disclosure (including the same-day-close
 * listing-price proxy, not the real IPO offer price); never drop it.
 */
export async function getIpoBoardsData(): Promise<IpoBoardsData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "ipo_boards.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as IpoBoardsData;
}
