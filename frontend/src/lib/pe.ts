import { idNum } from "@/lib/format";
import { relativeToTypical } from "@/lib/stock-summary";

/**
 * P/E is only meaningful for a company with positive earnings. A null or
 * P/E <= 0 (a loss-making company) must never be compared to a sector or
 * called cheap/expensive: the ratio is negative because earnings are.
 */
export const PE_NOT_APPLICABLE = "Tidak berlaku (rugi)";

export function isMeaningfulPe(pe: number | null | undefined): pe is number {
  return typeof pe === "number" && Number.isFinite(pe) && pe > 0;
}

/** "12,3x" for a meaningful P/E, otherwise "Tidak berlaku (rugi)". */
export function formatPe(pe: number | null | undefined): string {
  return isMeaningfulPe(pe) ? `${idNum(pe)}x` : PE_NOT_APPLICABLE;
}

/** "di atas" / "di bawah" ... vs the sector's typical P/E, or null when either side is not meaningful. */
export function peVsSector(own: number | null | undefined, sectorTypical: number | null | undefined): string | null {
  if (!isMeaningfulPe(own) || !isMeaningfulPe(sectorTypical)) return null;
  return relativeToTypical(own, sectorTypical);
}
