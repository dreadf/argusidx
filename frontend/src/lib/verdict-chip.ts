/** Client-safe verdict vocabulary (findings-data.ts reads files, so client components import from here). */
export type Verdict = "yes" | "no" | "mixed_or_inconclusive";

/** Verdict chip on the list (board Temuan-List-2): "Belum jelas" covers the mixed and inconclusive results. */
export const VERDICT_CHIP: Record<Verdict, { label: string; color: string }> = {
  yes: { label: "Terbukti", color: "var(--viz-diverging-pos)" },
  mixed_or_inconclusive: { label: "Belum jelas", color: "var(--viz-ink-muted)" },
  no: { label: "Tidak terbukti", color: "var(--viz-diverging-neg)" },
};
