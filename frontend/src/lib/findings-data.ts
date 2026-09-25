import { readFile } from "node:fs/promises";
import path from "node:path";

export type Verdict = "yes" | "no" | "mixed_or_inconclusive";

export interface FindingEvidence {
  hypothesis_id: string;
  n: string;
  period_id: string;
  limit_id: string;
}

export interface FindingRow {
  belief: string;
  verdict: Verdict;
  label: string;
  /** Plain-Bahasa beginner-facing copy — use these for display, not the
   * raw `belief`/`label` (research shorthand, see findings_translations.py). */
  belief_id: string;
  label_id: string;
  /** Short display copy for list rows (findings_translations.SHORT_COPY). */
  title_short_id: string;
  result_short_id: string;
  /** Sample size, period tested, and the one limit that matters most —
   * previously the scoreboard showed a verdict with no evidence behind
   * it at all (2026-09-19 usability audit). See findings_evidence.py. */
  evidence: FindingEvidence;
}

export interface FindingsData {
  source_file: string;
  scoreboard: FindingRow[];
}

/**
 * Reads data/app/findings.json, written by
 * pipeline/appdata/build_findings.py (parsed live from docs/PRODUCT.md's
 * honesty scoreboard table). Server-only (fs) — never import from a
 * "use client" component.
 */
export async function getFindingsData(): Promise<FindingsData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "findings.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as FindingsData;
}

/** URL slug for a finding's detail page, from its English research key. */
export function findingSlug(row: FindingRow): string {
  return row.belief
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export const VERDICT_TAB: Record<Verdict, { key: string; label: string }> = {
  yes: { key: "terbukti", label: "Terbukti" },
  mixed_or_inconclusive: { key: "tidak-konsisten", label: "Tidak konsisten" },
  no: { key: "tidak-terbukti", label: "Tidak terbukti" },
};
