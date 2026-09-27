/**
 * Shared display formatters. Extracted from `saham/[kode]/page.tsx` (which
 * had its own private copies) so the Ask layer can render the exact same
 * numbers, in the exact same words, without a second implementation
 * drifting from the first: the same "fix the class, not the instance"
 * discipline `pipeline/stats.py` documents on the Python side.
 */
export function formatMarketCap(value: number | null): string {
  if (value === null) return "tidak diketahui";
  const trillion = value / 1_000_000_000_000;
  if (trillion >= 1) return `Rp ${trillion.toFixed(1)} triliun`;
  const billion = value / 1_000_000_000;
  return `Rp ${billion.toFixed(0)} miliar`;
}

export function formatPrice(value: number | null): string {
  if (value === null) return "-";
  return `Rp ${value.toLocaleString("id-ID")}`;
}

export function formatPct(value: number | null, digits = 1): string {
  if (value === null) return "-";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Sectors symbols carry a ".JK" suffix internally (e.g. "BBCA.JK"); every
 * user-facing surface (links, table cells, labels) shows the bare code.
 * Centralized here so every *-data.ts loader normalizes it the same way,
 * instead of each call site remembering to strip it (or not). */
export function stripJk(symbol: string): string {
  return symbol.replace(/\.JK$/, "");
}

/* ---------------------------------------------------------------
 * Display helpers for the redesigned UI (added 2026-09-20). Additive:
 * the functions above are also used by the Ask layer, whose output
 * must not change, so these are separate rather than edits.
 * Indonesian number style (comma decimals) and an explicit minus on
 * every fall/gap/change; shares and probabilities stay unsigned.
 * --------------------------------------------------------------- */

/** 1234.5 -> "1.234,5" */
export function idNum(value: number, digits = 1): string {
  return value.toLocaleString("id-ID", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Percent-point value with an explicit sign: -27.7 -> "-27,7%", 4.2 with plus -> "+4,2%". */
export function signedPct(pointValue: number, digits = 1, plus = false): string {
  const rounded = Number(pointValue.toFixed(digits));
  if (rounded === 0) return `${idNum(0, digits)}%`;
  const body = idNum(Math.abs(rounded), digits);
  if (rounded < 0) return `-${body}%`;
  return `${plus ? "+" : ""}${body}%`;
}

/** Plain share/probability, no sign: 0.446 -> "44,6%". */
export function sharePct(ratio: number, digits = 1): string {
  return `${idNum(ratio * 100, digits)}%`;
}

/** Market value in trillions: 771917544337500 -> "Rp 771,9 T". */
export function rpTrillion(value: number, digits = 1): string {
  return `Rp ${idNum(value / 1_000_000_000_000, digits)} T`;
}

/** Percent-point distance of `price` from `reference` (negative = below). */
export function pctFrom(price: number, reference: number): number {
  return (price / reference - 1) * 100;
}

/** "2026-09-13" -> "13/09/2026" */
export function formatDateId(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/** "PT Bank Central Asia Tbk." -> "Bank Central Asia" (display only). */
export function shortName(name: string): string {
  return name
    .replace(/^PT\.?\s+/i, "")
    .replace(/\s*\(Persero\)/i, "")
    .replace(/\s+Tbk\.?$/i, "")
    .trim();
}
