import { readFile } from "node:fs/promises";
import path from "node:path";
import { formatDateId, formatPrice, idNum, shortName, signedPct } from "@/lib/format";
import { getSearchIndex } from "@/lib/stock-data";

/**
 * Per-stock situations from data/app/situations.json (built by the
 * pipeline; not the hub copy in lib/situations.ts). Server-only (fs).
 * `older_fall` is deliberately not a situation: a fall older than the
 * window is context, not something the stock is in now.
 */
export type SituationKey = "fall" | "loss_year" | "recent_price_suspension" | "recent_ipo" | "recent_spike" | "earnings_two_year_decline" | "earnings_more_than_doubled" | "long_below_peak" | "repeat_suspension";

export const SITUATION_KEYS: SituationKey[] = ["fall", "loss_year", "recent_price_suspension", "recent_ipo", "recent_spike", "earnings_two_year_decline", "earnings_more_than_doubled", "long_below_peak", "repeat_suspension"];

export interface FallInfo {
  peak_price: number;
  peak_date: string;
  trigger_date: string;
  trigger_price: number;
  trading_days_since: number;
  window_trading_days: number;
  last_close: number;
  last_close_date: string;
  pct_from_peak: number;
}
export interface LossYearInfo {
  year: number;
  net_income: number;
}
export interface SuspensionInfo {
  date: string;
  days_ago: number;
  pdf_url: string;
}
export interface IpoInfo {
  listing_date: string;
  board: string;
  days_since: number;
}
export interface SpikeInfo {
  event_date: string;
  trading_days_since: number;
  jump_pct: number;
  last_close: number;
  pct_since_event: number;
  lookback_trading_days: number;
}
export interface EarningsRunInfo {
  year: number;
  earnings: number[];
}

export interface LongBelowPeakInfo {
  peak_price: number;
  last_close: number;
  /** Fraction, negative: -0.36 is 36% below the old peak. */
  pct_below_peak: number;
  trading_days_since_trigger: number;
}
export interface RepeatSuspensionInfo {
  n_events: number;
  first_date: string;
  last_date: string;
}

export interface StockSituationEntry {
  fall: FallInfo | null;
  older_fall: FallInfo | null;
  loss_year: LossYearInfo | null;
  recent_price_suspension: SuspensionInfo | null;
  recent_ipo: IpoInfo | null;
  recent_spike: SpikeInfo | null;
  earnings_two_year_decline: EarningsRunInfo | null;
  earnings_more_than_doubled: EarningsRunInfo | null;
  long_below_peak: LongBelowPeakInfo | null;
  repeat_suspension: RepeatSuspensionInfo | null;
}

export interface SituationsFile {
  as_of: string;
  counts: Record<string, number>;
  definitions: Record<string, number>;
  by_symbol: Record<string, StockSituationEntry>;
}

let cached: SituationsFile | null = null;

export async function getSituationsFile(): Promise<SituationsFile> {
  if (cached === null) {
    const filePath = path.join(process.cwd(), "..", "data", "app", "situations.json");
    cached = JSON.parse(await readFile(filePath, "utf-8")) as SituationsFile;
  }
  return cached;
}

/** Situation keys a stock is currently in (non-null entries only). */
export function situationsOf(file: SituationsFile, code: string): SituationKey[] {
  const entry = file.by_symbol[`${code}.JK`];
  if (!entry) return [];
  return SITUATION_KEYS.filter((k) => entry[k] != null);
}

/** Situation page slug for each kind in situations.json. */
export const SLUG_BY_KIND: Record<SituationKey, string> = {
  fall: "turun-banyak",
  loss_year: "perusahaan-rugi",
  recent_price_suspension: "pernah-disuspensi",
  recent_ipo: "ikut-ipo",
  recent_spike: "harga-baru-melonjak",
  earnings_two_year_decline: "laba-turun-dua-tahun",
  earnings_more_than_doubled: "laba-dua-kali-lipat",
  long_below_peak: "bawah-puncak-lama",
  repeat_suspension: "langganan-suspensi",
};

export function kindOfSlug(slug: string): SituationKey | null {
  return (Object.entries(SLUG_BY_KIND).find(([, s]) => s === slug)?.[0] as SituationKey | undefined) ?? null;
}

/** Rupiah in Indonesian short form: 19122484264754 -> "19,1 T", 178e9 -> "178 M", 0.9e9 -> "0,9 M". */
export function rpShort(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${idNum(value / 1e12, 1)} T`;
  if (abs >= 1e9) return `${idNum(value / 1e9, abs >= 1e10 ? 0 : 1)} M`;
  return `${idNum(value / 1e6, 0)} jt`;
}

export interface SituationRow {
  code: string;
  name: string;
  /** Right column, main and sub line. */
  value: string;
  sub: string;
  /** ISO date for "Terbaru" ordering, when the situation has one. */
  date: string | null;
}

/** Everyone currently in one situation, with the two numbers a list row shows. */
export async function getSituationRows(kind: SituationKey): Promise<SituationRow[]> {
  const [file, index] = await Promise.all([getSituationsFile(), getSearchIndex()]);
  const name = new Map(index.map((e) => [e.code, shortName(e.name)]));
  const rows: SituationRow[] = [];
  for (const [symbol, entry] of Object.entries(file.by_symbol)) {
    const info = entry[kind];
    if (!info) continue;
    const code = symbol.replace(/\.JK$/, "");
    const base = { code, name: name.get(code) ?? code };
    if (kind === "recent_spike") {
      const i = info as SpikeInfo;
      rows.push({ ...base, value: signedPct(i.jump_pct, 1, true), sub: formatDateId(i.event_date), date: i.event_date });
    } else if (kind === "earnings_two_year_decline") {
      const i = info as EarningsRunInfo;
      rows.push({ ...base, value: `${rpShort(i.earnings[0])} ke ${rpShort(i.earnings[i.earnings.length - 1])}`, sub: `${i.year - 2} ke ${i.year}`, date: null });
    } else if (kind === "earnings_more_than_doubled") {
      const i = info as EarningsRunInfo;
      const [a, b] = i.earnings;
      rows.push({ ...base, value: a > 0 ? `x${idNum(b / a, b / a >= 10 ? 0 : 1)}` : "", sub: `${rpShort(a)} ke ${rpShort(b)}`, date: null });
    } else if (kind === "fall") {
      const i = info as FallInfo;
      rows.push({ ...base, value: signedPct(i.pct_from_peak), sub: `turun 30% pada ${formatDateId(i.trigger_date)}`, date: i.trigger_date });
    } else if (kind === "loss_year") {
      const i = info as LossYearInfo;
      rows.push({ ...base, value: `${rpShort(i.net_income)}`, sub: `rugi bersih ${i.year}`, date: null });
    } else if (kind === "long_below_peak") {
      const i = info as LongBelowPeakInfo;
      rows.push({ ...base, value: signedPct(i.pct_below_peak * 100), sub: `puncak ${formatPrice(i.peak_price)}`, date: null });
    } else if (kind === "repeat_suspension") {
      const i = info as RepeatSuspensionInfo;
      rows.push({ ...base, value: `${i.n_events} kali`, sub: `terakhir ${formatDateId(i.last_date)}`, date: i.last_date });
    } else if (kind === "recent_price_suspension") {
      const i = info as SuspensionInfo;
      rows.push({ ...base, value: `${i.days_ago} hari lalu`, sub: formatDateId(i.date), date: i.date });
    } else {
      const i = info as IpoInfo;
      rows.push({ ...base, value: `Papan ${i.board}`, sub: `listing ${formatDateId(i.listing_date)}`, date: i.listing_date });
    }
  }
  return rows;
}

/** The subtitle under a list header, per kind (board: Situasi-Baru-Daftar and the detail previews). */
export const LIST_SUB: Record<SituationKey, { title: string; sub: string; datedOrder: boolean }> = {
  recent_spike: { title: "saham sedang di sini", sub: "Naik 40% atau lebih dalam 20 hari bursa, dan lonjakan terakhir paling lama 20 hari bursa lalu.", datedOrder: true },
  earnings_two_year_decline: { title: "saham sedang di sini", sub: "Laba bersih dua tahun sebelumnya ke 2025 (Rp).", datedOrder: false },
  earnings_more_than_doubled: { title: "saham sedang di sini", sub: "Laba bersih 2024 ke 2025 (Rp).", datedOrder: false },
  fall: { title: "saham sedang di sini", sub: "Turun 30% atau lebih dari puncak dalam 252 hari bursa terakhir.", datedOrder: true },
  loss_year: { title: "perusahaan sedang di sini", sub: "Rugi bersih tahun 2025.", datedOrder: false },
  recent_price_suspension: { title: "saham sedang di sini", sub: "Disuspensi karena lonjakan harga dalam 90 hari terakhir.", datedOrder: true },
  recent_ipo: { title: "saham sedang di sini", sub: "Listing dalam 365 hari terakhir.", datedOrder: true },
  long_below_peak: { title: "saham sedang di sini", sub: "Pernah jatuh 30% atau lebih, dan sudah lebih dari 252 hari bursa di bawah puncak itu.", datedOrder: false },
  repeat_suspension: { title: "saham sedang di sini", sub: "Disuspensi karena lonjakan harga dua kali atau lebih.", datedOrder: true },
};
