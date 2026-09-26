import { formatMarketCap, idNum, signedPct } from "@/lib/format";
import type { StockPageData } from "@/lib/stock-data";
/**
 * Wording rules for the "Ringkasan" card on a stock page. Every phrase is
 * a deterministic comparison against a named yardstick, never a verdict:
 * no "good", "cheap" or "risky", and no row combines the others. If a
 * yardstick is missing, the row says less (or is left out); it never
 * guesses.
 */

/** "di atas" / "jauh di atas" / "di bawah" / "jauh di bawah" for own vs typical, ratio-based (2x or 0.5x is "jauh"). */
export function relativeToTypical(own: number, typical: number): string {
  if (typical > 0 && own > 0) {
    const ratio = own / typical;
    if (ratio >= 2) return "jauh di atas";
    if (ratio > 1) return "di atas";
    if (ratio <= 0.5) return "jauh di bawah";
    if (ratio < 1) return "di bawah";
    return "sama dengan";
  }
  if (own > typical) return "di atas";
  if (own < typical) return "di bawah";
  return "sama dengan";
}

/** Bullish share vs the market-wide share, in percentage points: within 3 = "sekitar sama", under 10 = "sedikit". */
export function newsRelative(sharePct: number, marketPct: number): string {
  const diff = sharePct - marketPct;
  if (Math.abs(diff) < 3) return "sekitar sama dengan";
  const dir = diff > 0 ? "di atas" : "di bawah";
  return Math.abs(diff) < 10 ? `sedikit ${dir}` : dir;
}

export function pricePosition(position: number | null): string | null {
  if (position === null) return null;
  if (position >= 0.8) return "Dekat tertinggi";
  if (position <= 0.2) return "Dekat terendah";
  return "Di tengah";
}

export function sizePhrase(marketCap: number | null, rank: number | null, universe: number): string | null {
  if (marketCap === null) return null;
  const value = formatMarketCap(marketCap).replace(".", ",");
  return rank === null ? `Nilai pasar ${value}.` : `Nilai pasar ${value}, terbesar ke-${rank} dari ${universe} saham.`;
}

export function fiveYearPhrase(bg: NonNullable<StockPageData["beat_gold"]>): { won: string[]; lost: string[] } {
  const items: [string, boolean | null][] = [
    ["indeks", bg.beat_index],
    ["emas", bg.beat_gold],
    ["deposito", bg.beat_deposit],
  ];
  return { won: items.filter(([, v]) => v === true).map(([k]) => k), lost: items.filter(([, v]) => v === false).map(([k]) => k) };
}

/** "Rp 12,4 M jual bersih, per 06/10/2026": one line of the foreign-flow row. Direction is a fact about the sign, not a call. */
export function foreignFlowLine(netIdr: number, asOf: string): string {
  const [year, month, day] = asOf.split("-");
  const abs = Math.abs(netIdr);
  const amount = abs >= 1e12 ? `${idNum(abs / 1e12, 1)} T` : `${idNum(abs / 1e9, 1)} M`;
  return `Rp ${amount} ${netIdr < 0 ? "jual" : "beli"} bersih, per ${day}/${month}/${year}`;
}

/** "Rp 100 ke Rp 560": offer price against the last close, for the IPO price row. */
export function ipoPriceLine(offerPrice: number, lastClose: number): string {
  return `Rp ${offerPrice.toLocaleString("id-ID")} ke Rp ${lastClose.toLocaleString("id-ID")}`;
}

export { idNum, signedPct };
