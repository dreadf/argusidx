import type { FindingRow } from "@/lib/findings-data";

/**
 * Trial counter: EXPERIMENT.md ("Trial count: 35", H18). It is not in
 * data/app/findings.json, which only lists the 19 beliefs, so it is
 * pinned here like the other constants in lib/situations.ts. Update it
 * together with EXPERIMENT.md.
 */
export const TRIAL_COUNT = 35;

export function summarizeFindings(scoreboard: FindingRow[]): { beliefs: number; proven: number } {
  return { beliefs: scoreboard.length, proven: scoreboard.filter((r) => r.verdict === "yes").length };
}
