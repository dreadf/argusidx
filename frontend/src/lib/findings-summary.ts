import type { FindingRow } from "@/lib/findings-data";

/**
 * Trial counter: EXPERIMENT.md ("Trial counter: 39", A1, 2026-09-27). It is
 * not in data/app/findings.json, which only lists the 23 beliefs, so it
 * is pinned here like the other constants in lib/situations.ts. Update it
 * together with EXPERIMENT.md.
 */
export const TRIAL_COUNT = 39;

export function summarizeFindings(scoreboard: FindingRow[]): { beliefs: number; proven: number } {
  return { beliefs: scoreboard.length, proven: scoreboard.filter((r) => r.verdict === "yes").length };
}
