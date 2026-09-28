import { dateLong } from "@/lib/dates";
import { formatPrice, idNum, pctFrom, signedPct } from "@/lib/format";
import type { BaseRatesData } from "@/lib/base-rates-data";
import type { FindingRow, Verdict } from "@/lib/findings-data";
import { findingSlug } from "@/lib/findings-data";
import type { IpoBoardsData } from "@/lib/ipo-boards-data";
import { isMeaningfulPe } from "@/lib/pe";
import { H11_UNDERPERFORM } from "@/lib/situations";
import type { Answer, Evidence, Purpose } from "@/lib/purposes";
import type { StockPageData } from "@/lib/stock-data";
import type { ProfileMeta, StockProfile } from "@/lib/stock-profile-data";
import { SLUG_BY_KIND, type StockSituationEntry } from "@/lib/stock-situations";

/**
 * The stock page's reading of one stock (board Baru4-Saham-*): the
 * Kesimpulan, the popular signals present in the stock with their test
 * result, the situations to note, the answer for each "why are you looking"
 * chip, and the Tanya suggestions. Pure functions of the data, so every
 * stock gets the same fixed rules and the rules are unit-tested.
 *
 * Constraints (CLAUDE.md): labels describe states, never actions; no
 * combined score (each row and item stands on its own); a verdict is always
 * the one in findings.json; frequencies are past base rates, not forecasts.
 */

/* ------------------------------------------------------------------ inputs */

export type SignalKey = "low_pe" | "high_yield" | "small" | "high_roe" | "high_debt" | "fast_revenue" | "earnings_up" | "foreign_buy" | "insider_buy" | "news_tone" | "thin_float" | "top_gainer";
/** Findings used outside the signal list (answers). */
export type ExtraFindingKey = "oversold" | "ma200" | "momentum" | "market_state" | "payout_worse" | "spike_suspension";
export type FindingKey = SignalKey | ExtraFindingKey;

/** Each key's finding in findings.json, by its research `belief` (stable across copy edits). */
export const FINDING_BELIEF: Record<FindingKey, string> = {
  low_pe: "Cheap stocks (low P/E) do better",
  high_yield: "High dividend yield means better returns",
  small: "Small companies earn more",
  high_roe: "High ROE (quality) predicts better returns",
  high_debt: "High leverage (debt/equity) predicts worse returns",
  fast_revenue: "Fast revenue growth predicts better returns",
  earnings_up: "Rising profits mean a rising share price",
  foreign_buy: "Foreign investors buying heavily means the price will rise",
  insider_buy: "Insiders buying their own stock means the price will rise",
  news_tone: "Positive news coverage predicts a stock will rise",
  thin_float: "Thin float means wild swings",
  top_gainer: "The stocks that gained the most today keep rising",
  oversold: "Oversold (RSI < 30) means a bounce",
  ma200: "Price above its 200-day average keeps going up",
  momentum: "Recent 60-day momentum predicts next month",
  market_state: 'Once IHSG looks "tertekan" (pressured), a further fall is more likely than a recovery',
  payout_worse: "High payout ratio predicts worse returns",
  spike_suspension: "A stock suspended for a sudden price spike keeps rising",
};

export interface FindingRef {
  verdict: Verdict;
  href: string;
}

export function findingRefs(rows: FindingRow[]): Record<FindingKey, FindingRef> {
  const out = {} as Record<FindingKey, FindingRef>;
  for (const key of Object.keys(FINDING_BELIEF) as FindingKey[]) {
    const row = rows.find((r) => r.belief === FINDING_BELIEF[key]);
    if (!row) throw new Error(`findings.json has no finding "${FINDING_BELIEF[key]}" (${key})`);
    out[key] = { verdict: row.verdict, href: `/temuan/${findingSlug(row)}` };
  }
  return out;
}

export interface ReadInput {
  code: string;
  /** Indonesian sector label ("Industri"), or null when unknown. */
  sector: string | null;
  data: StockPageData;
  profile: StockProfile;
  meta: ProfileMeta;
  situations: StockSituationEntry | undefined;
  base: BaseRatesData;
  ipo: IpoBoardsData;
  yieldCut: { rate: number | null; n: number | null; year: string };
  findings: Record<FindingKey, FindingRef>;
  news: { bullish: number; bearish: number } | null;
  newsMarket: { bullishPct: number; first: string; last: string };
  market: { state: string; pct_from_peak: number };
  gainRankCount: number;
  universe: number;
  insiderSince: string;
  /** How many stocks are in each situation or flag now (situations.json counts, flags.json flagged_count). */
  nowCounts: Record<string, number>;
}

/* ------------------------------------------------------------------ words */

export { dateLong };

/** Signed percent from a fraction: -0.109 -> "-10,9%", 0.93 -> "+93,0%". */
export function pctSigned(frac: number, digits = 1): string {
  return signedPct(frac * 100, digits, true);
}

/** Unsigned percent from a fraction: 0.0794 -> "7,9%". */
export function pctPlain(frac: number, digits = 1): string {
  return `${idNum(Math.abs(frac) * 100, digits)}%`;
}

/** Rupiah amounts in words the page uses: "Rp 32,8 T", "Rp 268 M", "Rp 950 jt". */
export function rpAmount(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e12) return `Rp ${idNum(abs / 1e12, 1)} T`;
  if (abs >= 1e9) return `Rp ${idNum(abs / 1e9, abs >= 1e10 ? 0 : 1)} M`;
  return `Rp ${idNum(abs / 1e6, 0)} jt`;
}

const of100 = (share: number) => Math.round(share);

/**
 * A change in words: "naik 83%", "turun 4,2%", and from +100% up
 * "naik menjadi 12,3 kali lipat", which a beginner reads more easily than
 * "naik 1.127%".
 */
export function changeWords(frac: number, digits = 1): string {
  if (frac >= 1) return `naik menjadi ${idNum(1 + frac, 1)} kali lipat`;
  return `${frac < 0 ? "turun" : "naik"} ${pctPlain(frac, digits)}`;
}

/** Share of profit paid out, in words: "80% dari labanya", or "19 kali labanya" once it passes 200%. */
export function payoutWords(ratio: number): string {
  return ratio >= 2 ? `${idNum(ratio, 1)} kali labanya` : `${idNum(ratio * 100, 0)}% dari labanya`;
}
const lower = (s: string | null) => (s ? s.toLowerCase() : "");

function sectorStocks(r: ReadInput): string {
  return r.sector ? `saham ${lower(r.sector)}` : "saham di sektornya";
}

/* ------------------------------------------------------------------ earnings and dividend shapes */

const Y = { last: 4, prev: 3, prev2: 2 };

export type EarningsShape = "none" | "loss_shrinking" | "loss_growing" | "turned_loss" | "loss" | "back_to_profit" | "rising_every_year" | "falling_two_years" | "stable_near_high" | "stable" | "up" | "down" | "profit";

export function earningsShape(e: (number | null)[]): EarningsShape {
  const last = e[Y.last];
  const prev = e[Y.prev];
  if (last === null) return "none";
  if (last < 0) {
    if (prev === null) return "loss";
    if (prev < 0) return Math.abs(last) < Math.abs(prev) ? "loss_shrinking" : "loss_growing";
    return "turned_loss";
  }
  if (prev === null) return "profit";
  if (prev < 0) return "back_to_profit";
  // Longest run of reported, positive, strictly rising years ending in 2025.
  let start = Y.last;
  while (start > 0 && e[start - 1] !== null && (e[start - 1] as number) > 0 && (e[start - 1] as number) < (e[start] as number)) start--;
  if (Y.last - start >= 2) return "rising_every_year";
  const prev2 = e[Y.prev2];
  if (prev2 !== null && prev2 > prev && prev > last && last > 0) return "falling_two_years";
  if (prev === 0) return "profit";
  const yoy = last / prev - 1;
  if (Math.abs(yoy) <= 0.05) {
    const max = Math.max(...e.filter((v): v is number => v !== null));
    return last >= 0.9 * max ? "stable_near_high" : "stable";
  }
  return yoy > 0 ? "up" : "down";
}

/** First year of the rising run (for "naik setiap tahun sejak ..."). */
function risingSince(e: (number | null)[], years: number[]): number {
  let start = Y.last;
  while (start > 0 && e[start - 1] !== null && (e[start - 1] as number) > 0 && (e[start - 1] as number) < (e[start] as number)) start--;
  return years[start];
}

export type DividendShape = "never" | "every_year_falling" | "every_year_rising" | "every_year" | "first_time" | "not_every_year" | "skipped_latest";

export function dividendShape(d: (number | null)[]): DividendShape {
  const paid = d.map((v) => v !== null && v > 0);
  if (!paid.some(Boolean)) return "never";
  if (!paid[Y.last]) return "skipped_latest";
  if (paid.every(Boolean)) {
    const [a, b, c] = [d[Y.prev2] as number, d[Y.prev] as number, d[Y.last] as number];
    if (a > b && b > c) return "every_year_falling";
    if (c > b) return "every_year_rising";
    return "every_year";
  }
  if (paid.filter(Boolean).length === 1) return "first_time";
  return "not_every_year";
}

/* ------------------------------------------------------------------ Kesimpulan */

/**
 * The Kesimpulan's fixed rules (plan kind-juggling-hoare.md §6), so every
 * stock is read the same way:
 *
 * 1. Headline: the one-year price change against IHSG and against the
 *    stock's own sector. Words once here; the numbers for both fixed
 *    windows (one year, and since the IHSG peak) sit in a figure strip
 *    under it, and the dates and exact sector rank in the caption.
 * 2. "Perlu diperhatikan": every situation and flag named one by one, never
 *    counted (R2a did not qualify as a test, EXPERIMENT.md 2026-09-27, so no
 *    count may be shown). Order is WATCH_ORDER.
 * 3. Under it, the rarest of them right now (fewest stocks in it), and
 *    how many stocks share it. Its frequency is in the section below, said
 *    once, so the plan's 100-case minimum (which was for showing a rate
 *    here) no longer applies.
 *
 * Then the Laba / Valuasi / Dividen facts. Each row stands on its own.
 */

export interface RingkasanRow {
  label: string;
  state: string;
  explain: string;
}

export interface KesimpulanFigure {
  label: string;
  stock: number;
  ihsg: number;
}

export interface Kesimpulan {
  headline: string;
  /** The stock and IHSG over the two fixed windows: one year, and since the IHSG peak. */
  figures: KesimpulanFigure[];
  /** Window and exact sector rank, the numbers behind the headline's words. */
  caption: string | null;
  /** Names, one by one. */
  watch: string[];
  /** Line 3: the rarest situation now, and how many stocks are in it. */
  rarest: string | null;
  rows: RingkasanRow[];
}


function labaRow(r: ReadInput): RingkasanRow {
  const e = r.profile.earnings;
  const years = r.meta.years;
  const last = e[Y.last];
  const prev = e[Y.prev];
  const shape = earningsShape(e);
  const yoyText = () => {
    if (last === null || prev === null || prev <= 0) return "";
    const yoy = last / prev - 1;
    return `, ${changeWords(yoy, 0)} dari ${years[Y.prev]}`;
  };
  switch (shape) {
    case "none": {
      const i = e.map((v, k) => (v === null ? -1 : k)).filter((k) => k >= 0).pop();
      return { label: "Laba", state: "Belum ada laporan 2025", explain: i === undefined ? "Belum ada laporan laba tahunan." : `Laporan terakhir ${years[i]}: ${(e[i] as number) < 0 ? "rugi" : "laba"} ${rpAmount(e[i] as number)}.` };
    }
    case "loss_shrinking":
      return { label: "Laba", state: "Rugi, tapi menyusut", explain: `Rugi ${rpAmount(last!)} pada ${years[Y.last]}, dari rugi ${rpAmount(prev!)} pada ${years[Y.prev]}.` };
    case "loss_growing":
      return { label: "Laba", state: "Rugi, dan membesar", explain: `Rugi ${rpAmount(last!)} pada ${years[Y.last]}, dari rugi ${rpAmount(prev!)} pada ${years[Y.prev]}.` };
    case "turned_loss":
      return { label: "Laba", state: "Berbalik rugi", explain: `Rugi ${rpAmount(last!)} pada ${years[Y.last]}, setelah laba ${rpAmount(prev!)} pada ${years[Y.prev]}.` };
    case "loss":
      return { label: "Laba", state: "Rugi", explain: `Rugi ${rpAmount(last!)} pada ${years[Y.last]}.` };
    case "back_to_profit":
      return { label: "Laba", state: "Kembali untung", explain: `Laba ${rpAmount(last!)} pada ${years[Y.last]}, setelah rugi ${rpAmount(prev!)} pada ${years[Y.prev]}.` };
    case "rising_every_year":
      return { label: "Laba", state: `Naik setiap tahun sejak ${risingSince(e, years)}`, explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}.` };
    case "falling_two_years":
      return { label: "Laba", state: "Turun dua tahun berturut-turut", explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}. Tahun ${years[Y.prev2]} ${rpAmount(e[Y.prev2]!)}.` };
    case "stable_near_high":
      return { label: "Laba", state: "Stabil, dekat tertinggi lima tahun", explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}.` };
    case "stable":
      return { label: "Laba", state: "Stabil", explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}.` };
    case "up":
      return { label: "Laba", state: last! >= 2 * prev! ? "Lebih dari dua kali lipat" : `Naik dari ${years[Y.prev]}`, explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}.` };
    case "down":
      return { label: "Laba", state: `Turun dari ${years[Y.prev]}`, explain: `${rpAmount(last!)} pada ${years[Y.last]}${yoyText()}.` };
    default:
      return { label: "Laba", state: "Untung", explain: `${rpAmount(last!)} pada ${years[Y.last]}.` };
  }
}

/** Why a stock has no usable P/E: a loss, earnings near zero, or simply no value recorded. */
export function peMissingReason(p: StockProfile): "loss" | "near_zero" | "missing" {
  const last = p.earnings[Y.last];
  if ((last !== null && last < 0) || (p.pe_ttm !== null && p.pe_ttm <= 0)) return "loss";
  if (p.pe_ttm === null) return "missing";
  return "near_zero";
}

function valuasiRow(r: ReadInput): RingkasanRow {
  const { profile, data } = r;
  const pb = profile.pb_mrq;
  const pbText = pb !== null && pb > 0 ? ` P/B ${idNum(pb, 2)}x: harga Rp ${idNum(pb, 2)} untuk tiap Rp 1 modal.` : "";
  if (!profile.pe_meaningful || profile.pe_ttm === null) {
    const why = peMissingReason(profile);
    if (why === "missing") return { label: "Valuasi", state: "P/E tidak tersedia", explain: `P/E ${r.code} tidak tercatat di data kami.${pbText}` };
    return { label: "Valuasi", state: "P/E tidak bermakna", explain: `${why === "loss" ? "Perusahaan rugi, jadi P/E tidak bisa dipakai." : "Laba hampir nol, jadi P/E tidak bisa dipakai."}${pbText}` };
  }
  const pe = profile.pe_ttm;
  const spe = data.sector_context?.sector_typical_pe ?? null;
  const base = `Harga Rp ${idNum(pe)} untuk tiap Rp 1 laba setahun.`;
  if (!isMeaningfulPe(spe)) return { label: "Valuasi", state: `P/E ${idNum(pe)}x`, explain: base };
  const ratio = pe / spe;
  const state = ratio < 0.8 ? "P/E di bawah sektornya" : ratio > 3 ? "P/E jauh di atas sektornya" : ratio > 1.25 ? "P/E di atas sektornya" : "P/E setara sektornya";
  return { label: "Valuasi", state, explain: `${base} Nilai tengah sektor Rp ${idNum(spe)}.` };
}

function dividenRow(r: ReadInput): RingkasanRow {
  const d = r.profile.dividend;
  const years = r.meta.years;
  const shape = dividendShape(d);
  const y = r.profile.yield_ttm;
  const yieldText = y !== null && y > 0 ? ` Imbal 12 bulan terakhir ${pctPlain(y)} dari harga.` : "";
  if (shape === "never") return { label: "Dividen", state: "Tidak membagikan", explain: `Tidak ada dividen tercatat dari ${years[0]} sampai ${years[Y.last]}.` };
  if (shape === "skipped_latest") {
    const i = d.map((v, k) => (v !== null && v > 0 ? k : -1)).filter((k) => k >= 0).pop()!;
    return { label: "Dividen", state: `Tidak membagikan untuk ${years[Y.last]}`, explain: `Terakhir Rp ${idNum(d[i]!, d[i]! < 10 ? 2 : 0)} per saham untuk ${years[i]}.${yieldText}` };
  }
  const last = d[Y.last]!;
  const max = Math.max(...d.filter((v): v is number => v !== null));
  const maxYear = years[d.indexOf(max)];
  const peak = max > last ? ` Tertinggi Rp ${idNum(max, max < 10 ? 2 : 0)} (${maxYear}).` : "";
  const state: Record<Exclude<DividendShape, "never" | "skipped_latest">, string> = {
    every_year_falling: "Rutin, tapi turun dua tahun",
    every_year_rising: "Rutin, dan naik",
    every_year: "Dibayar setiap tahun",
    first_time: "Baru sekali",
    not_every_year: "Tidak setiap tahun",
  };
  return { label: "Dividen", state: state[shape], explain: `Rp ${idNum(last, last < 10 ? 2 : 0)} per saham untuk ${years[Y.last]}.${yieldText}${peak}` };
}

/** How the stock moved against a benchmark, as the adjective the headline uses. */
function versus(chg: number, other: number): "sejalan" | "worse" | "better" {
  if (Math.abs(chg - other) <= 0.03) return "sejalan";
  return chg > other ? "better" : "worse";
}

function headline(r: ReadInput): { headline: string; caption: string | null } {
  const { profile, meta, code } = r;
  const chg = profile.change_1y;
  if (chg === null) {
    const ipo = r.situations?.recent_ipo;
    return { headline: ipo ? `${code} baru melantai ${dateLong(ipo.listing_date)}, jadi perubahan harganya setahun belum bisa dihitung.` : `Perubahan harga ${code} setahun tidak tersedia.`, caption: null };
  }
  const ihsg = meta.ihsg_change_1y;
  const falling = chg < 0;
  const adj = (v: "worse" | "better") => (falling ? (v === "worse" ? "lebih dalam" : "lebih ringan") : v === "worse" ? "lebih rendah" : "lebih tinggi");
  const vsI = versus(chg, ihsg);
  let text: string;
  if (vsI === "sejalan") text = `sejalan dengan IHSG (${pctSigned(ihsg)})`;
  else if (!falling && ihsg < 0) text = `saat IHSG turun (${pctSigned(ihsg)})`;
  else text = `${adj(vsI)} dari IHSG (${pctSigned(ihsg)})`;

  const rank = profile.sector_rank_1y;
  let sectorText = "";
  if (rank && rank.n >= 5) {
    const share = rank.better / rank.n;
    const vsS: "worse" | "better" | null = share >= 2 / 3 ? "worse" : share <= 1 / 3 ? "better" : null;
    if (vsS) {
      const most = share >= 0.9 || share <= 0.1 ? "hampir semua" : "kebanyakan";
      const who = `${most} ${sectorStocks(r)}`;
      // "dan dari" only attaches to a comparison ("lebih dalam dari IHSG"), where the
      // adjective right before it already carries the verb by proximity. After
      // "sejalan dengan IHSG" or "saat IHSG turun" that adjective is many words from
      // "turun"/"naik" at the sentence's start, so the verb is repeated here --
      // otherwise "lebih dalam dari X" reads with no clear antecedent (found from a
      // first read of the live copy, 2026-09-28: "sejalan dengan IHSG, tapi lebih
      // dalam dari saham keuangan" -- "lebih dalam [apa]?").
      const comparative = vsI !== "sejalan" && !(!falling && ihsg < 0);
      const verbed = `${falling ? "turun" : "naik"} ${adj(vsS)}`;
      if (!comparative) sectorText = `, dan ${verbed} dari ${who}`;
      else if (vsI === vsS) sectorText = ` dan dari ${who}`;
      else sectorText = `, tapi ${verbed} dari ${who}`;
    }
  }
  const peers = rank && rank.n > 1 ? ` Dalam setahun, ${rank.better === 0 ? `tidak ada ${sectorStocks(r)} lain yang` : `${rank.better} dari ${rank.n} ${sectorStocks(r)}`} bergerak lebih baik.` : "";
  return {
    headline: `Harga ${code} ${changeWords(chg)} dalam setahun, ${text}${sectorText}.`,
    caption: `Harga penutupan dari Sectors sampai ${dateLong(meta.change_window.end)}.${peers}`,
  };
}

/** Line 3: the situation the fewest stocks are in right now; ties go to the earlier one in WATCH_ORDER. */
export function rarestItem(r: ReadInput, watch: WatchItem[]): WatchItem | null {
  const known = watch.filter((w) => r.nowCounts[w.kind] !== undefined);
  if (known.length === 0) return null;
  return known.reduce((a, b) => (r.nowCounts[b.kind] < r.nowCounts[a.kind] ? b : a));
}

export function kesimpulan(r: ReadInput, watch: WatchItem[]): Kesimpulan {
  const h = headline(r);
  const top = rarestItem(r, watch);
  const rarest = top
    ? `${watch.length > 1 ? `Paling jarang: ${top.title.toLowerCase()}, keadaan yang sedang dialami` : "Keadaan ini sedang dialami"} ${r.nowCounts[top.kind]} dari ${r.universe} saham.`
    : null;
  const { profile: p, meta } = r;
  const figures: KesimpulanFigure[] = [];
  if (p.change_1y !== null) figures.push({ label: "Setahun", stock: p.change_1y, ihsg: meta.ihsg_change_1y });
  if (p.change_since_peak !== null) figures.push({ label: `Sejak puncak IHSG, ${dateLong(meta.peak_window.start)}`, stock: p.change_since_peak, ihsg: meta.ihsg_change_since_peak });
  return {
    headline: h.headline,
    figures,
    caption: h.caption,
    watch: watch.map((w) => w.title),
    rarest,
    rows: [labaRow(r), valuasiRow(r), dividenRow(r)],
  };
}


/* ------------------------------------------------------------------ Sinyal populer */

export interface Signal {
  key: SignalKey;
  title: string;
  /** What the stock shows, as one plain sentence. */
  here: string;
  /** "Hasil uji:" line. */
  result: string;
  verdict: Verdict;
  /** "Artinya untuk ASII:" line, only when it adds something the test result does not say. */
  meaning: string | null;
  href: string;
}

/**
 * The verdict each result line was written for. A test fails if
 * findings.json ever disagrees, so the copy cannot drift from the verdict.
 */
export const SIGNAL_VERDICT: Record<SignalKey, Verdict> = {
  low_pe: "yes",
  high_yield: "yes",
  small: "yes",
  high_roe: "no",
  high_debt: "no",
  fast_revenue: "no",
  earnings_up: "no",
  foreign_buy: "no",
  insider_buy: "no",
  news_tone: "mixed_or_inconclusive",
  thin_float: "no",
  top_gainer: "no",
};

const RESULT: Record<SignalKey, string> = {
  low_pe: "saham P/E rendah rata-rata memberi hasil sedikit lebih baik. Pengaruhnya kecil.",
  high_yield: "saham berdividen tinggi rata-rata memberi hasil sedikit lebih baik. Pengaruhnya kecil.",
  small: "perusahaan kecil rata-rata memberi hasil lebih baik, tapi lebih lemah dari perkiraan.",
  high_roe: "ROE tinggi tidak terbukti diikuti hasil yang lebih baik.",
  high_debt: "utang tinggi tidak terbukti diikuti hasil yang lebih buruk.",
  fast_revenue: "pendapatan yang tumbuh cepat tidak terbukti diikuti hasil yang lebih baik.",
  earnings_up: "laba naik tidak terbukti diikuti kenaikan harga sesudahnya.",
  foreign_buy: "saham di daftar beli bersih asing tidak naik lebih dari saham di daftar jual bersih asing.",
  insider_buy: "setelah orang dalam membeli, harga tidak lebih sering mengalahkan IHSG.",
  news_tone: "nada berita, positif maupun negatif, belum terbukti memprediksi arah harga. Hasilnya berbalik antar paruh data.",
  thin_float: "float kecil tidak membuat harga lebih bergejolak; yang terlihat justru sebaliknya. Diukur bersamaan, bukan ramalan.",
  top_gainer: "saham yang naik paling tinggi dalam sehari tidak terbukti terus naik sebulan sesudahnya.",
};

const TOP_THIRD = 200 / 3;

/**
 * Dividend over profit. The "Dividen melebihi laba" flag is computed from
 * the 2025 totals and stores its own ratio, which can differ from the
 * snapshot payout_ratio; when the flag is on, its ratio is the one shown, so
 * the page never says "melebihi laba" next to "membagikan 42%".
 */
export function payoutOf(r: ReadInput): number | null {
  const flagged = r.data.flags.find((f) => f.key === "payout_above_earnings")?.detail.payout_ratio;
  return typeof flagged === "number" ? flagged : r.profile.payout_ratio;
}

/** Top third among dividend payers (most stocks pay nothing, so all-stock rank would call 0,2% "high"). */
export function isHighYield(p: StockProfile): boolean {
  return p.yield_ttm !== null && p.yield_ttm > 0 && p.yield_higher_than_payers !== null && p.yield_higher_than_payers >= TOP_THIRD;
}
const SIGNAL_ORDER: Verdict[] = ["yes", "no", "mixed_or_inconclusive"];

/** Own P/E history at year ends (meaningful values only), for "rendahnya bukan hal baru". */
function ownPeRange(p: StockProfile, years: number[]): { from: number; min: number; max: number } | null {
  const vals = p.pe.map((v, i) => ({ v, y: years[i] })).filter((x): x is { v: number; y: number } => isMeaningfulPe(x.v));
  if (vals.length < 3) return null;
  return { from: vals[0].y, min: Math.min(...vals.map((x) => x.v)), max: Math.max(...vals.map((x) => x.v)) };
}

export function popularSignals(r: ReadInput, watch: WatchItem[]): Signal[] {
  const { code, profile: p, meta, data } = r;
  const out: Omit<Signal, "verdict" | "href" | "result">[] = [];
  const e = p.earnings;
  const years = meta.years;

  if (p.pe_meaningful && p.pe_cheaper_than !== null && p.pe_cheaper_than >= TOP_THIRD && p.pe_ttm !== null) {
    const spe = data.sector_context?.sector_typical_pe ?? null;
    const range = ownPeRange(p, years);
    const usual = range && p.pe_ttm >= range.min * 0.9 ? ` P/E ${code} di akhir tahun ${range.from} sampai ${years[Y.last]} berkisar ${idNum(range.min)}x sampai ${idNum(range.max)}x, jadi rendahnya bukan hal baru.` : "";
    out.push({
      key: "low_pe",
      title: `P/E ${code} rendah`,
      here: `P/E ${idNum(p.pe_ttm)}x, lebih rendah dari ${of100(p.pe_cheaper_than)}% saham berlaba.${isMeaningfulPe(spe) ? ` Nilai tengah sektornya ${idNum(spe)}x.` : ""}`,
      meaning: usual ? usual.trim() : null,
    });
  }
  if (isHighYield(p) && p.yield_ttm !== null) {
    const d = p.dividend;
    const falling = dividendShape(d) === "every_year_falling";
    const spike = watch.some((w) => w.kind === "yield_far_above_average");
    const why = spike
      ? ` Imbal ${code} sekarang jauh di atas rata-ratanya sendiri; lihat catatannya di bagian berikut.`
      : falling
        ? ` Dividen per saham ${code} sudah turun dua tahun (Rp ${idNum(d[Y.prev2]!, d[Y.prev2]! < 10 ? 2 : 0)} ke Rp ${idNum(d[Y.last]!, d[Y.last]! < 10 ? 2 : 0)}).`
        : "";
    out.push({
      key: "high_yield",
      title: `Dividen ${code} tinggi`,
      here: `Imbal dividen ${pctPlain(p.yield_ttm)}, lebih tinggi dari ${of100(p.yield_higher_than)}% saham.`,
      meaning: `Imbal ini dihitung dari dividen 12 bulan terakhir, bukan janji dividen berikutnya.${why}`,
    });
  }
  if (p.size_third === "small" && data.snapshot.market_cap !== null && data.snapshot.market_cap_rank !== null) {
    out.push({
      key: "small",
      title: `${code} perusahaan kecil`,
      here: `Nilai pasar ${rpAmount(data.snapshot.market_cap)}, peringkat ke-${data.snapshot.market_cap_rank} dari ${r.universe}.`,
      meaning: null,
    });
  }
  if (p.roe_ttm !== null && p.roe_ttm > 0 && p.roe_higher_than !== null && p.roe_higher_than >= TOP_THIRD) {
    out.push({
      key: "high_roe",
      title: `ROE ${code} tinggi`,
      here: `ROE ${pctPlain(p.roe_ttm)}: setiap Rp 100 modal menghasilkan Rp ${idNum(p.roe_ttm * 100, 0)} laba setahun. Lebih tinggi dari ${of100(p.roe_higher_than)}% saham.`,
      meaning: null,
    });
  }
  if (p.der_mrq !== null && p.der_higher_than !== null && p.der_higher_than >= TOP_THIRD) {
    out.push({
      key: "high_debt",
      title: `Utang ${code} tinggi`,
      here: `Utang ${idNum(p.der_mrq, 2)}x modal, lebih tinggi dari ${of100(p.der_higher_than)}% perusahaan non-keuangan.`,
      meaning: null,
    });
  }
  if (p.revenue_growth !== null && p.revenue_growth > 0 && p.revenue_growth_higher_than !== null && p.revenue_growth_higher_than >= TOP_THIRD) {
    out.push({
      key: "fast_revenue",
      title: `Pendapatan ${code} tumbuh cepat`,
      here: `Pendapatan ${years[Y.last]} ${changeWords(p.revenue_growth)} dari ${years[Y.prev]}, lebih cepat dari ${of100(p.revenue_growth_higher_than)}% perusahaan.`,
      meaning: null,
    });
  }
  const last = e[Y.last];
  const prev = e[Y.prev];
  if (last !== null && prev !== null && prev > 0 && last > prev) {
    const yoy = last / prev - 1;
    const chg = p.change_1y;
    const vsPrice = chg === null ? "" : `, sementara harganya ${changeWords(chg)} dalam setahun`;
    out.push({
      key: "earnings_up",
      title: `Laba ${code} naik`,
      here: `Laba ${years[Y.last]} ${changeWords(yoy, 0)} dari ${years[Y.prev]}${vsPrice}.`,
      meaning: null,
    });
  }
  if (p.foreign_buy_days >= 10 && p.foreign_buy_days >= 1.5 * p.foreign_sell_days) {
    out.push({
      key: "foreign_buy",
      title: `Asing sering membeli ${code}`,
      here: `Di daftar beli bersih asing ${p.foreign_buy_days} hari, daftar jual bersih ${p.foreign_sell_days} hari (dari ${meta.foreign_flow.days} hari).`,
      meaning: null,
    });
  }
  const ins = data.insider_activity;
  if (ins && ins.net_direction === "net_buying") {
    out.push({
      key: "insider_buy",
      title: `Orang dalam ${code} membeli`,
      here: `${ins.buy_count} laporan beli dan ${ins.sell_count} laporan jual sejak ${dateLong(r.insiderSince)}${ins.last_transaction_date ? `, terakhir ${dateLong(ins.last_transaction_date)}` : ""}.`,
      meaning: null,
    });
  }
  const n = r.news;
  if (n && n.bullish + n.bearish >= 20 && n.bullish !== n.bearish) {
    const pos = n.bullish > n.bearish;
    const share = (n.bullish / (n.bullish + n.bearish)) * 100;
    out.push({
      key: "news_tone",
      title: `Berita tentang ${code} lebih banyak ${pos ? "positif" : "negatif"}`,
      here: `${n.bullish} artikel positif dan ${n.bearish} negatif dari ${dateLong(r.newsMarket.first)} sampai ${dateLong(r.newsMarket.last)}: ${idNum(share, 0)}% positif, sementara rata-rata semua saham ${idNum(r.newsMarket.bullishPct, 0)}%. Nada artikel dilabeli Sectors.`,
      meaning: null,
    });
  }
  if (data.h1_finding?.free_float_tercile === "low" && data.snapshot.free_float !== null) {
    out.push({
      key: "thin_float",
      title: `Free float ${code} kecil`,
      here: `Free float ${idNum(data.snapshot.free_float * 100)}%, sepertiga tersempit untuk ukuran perusahaannya.`,
      meaning: null,
    });
  }
  const gain = p.daily_close_change;
  if (p.daily_gain_rank !== null && p.daily_gain_rank <= 10 && gain !== null && gain > 0) {
    out.push({
      key: "top_gainer",
      title: `${code} naik paling tinggi hari ini`,
      here: `Naik ${pctPlain(gain)} pada ${dateLong(meta.as_of)}, peringkat ${p.daily_gain_rank} dari ${r.gainRankCount} saham.`,
      meaning: null,
    });
  }
  return out
    .map((s) => ({ ...s, verdict: r.findings[s.key].verdict, href: r.findings[s.key].href, result: RESULT[s.key] }))
    .sort((a, b) => SIGNAL_ORDER.indexOf(a.verdict) - SIGNAL_ORDER.indexOf(b.verdict));
}

/* ------------------------------------------------------------------ Yang perlu diperhatikan */

export type WatchKind =
  | "fall"
  | "long_below_peak"
  | "recent_price_suspension"
  | "repeat_suspension"
  | "recent_spike"
  | "loss_year"
  | "earnings_two_year_decline"
  | "recent_ipo"
  | "earnings_more_than_doubled"
  | "payout_above_earnings"
  | "near_ath_earnings_decline"
  | "yield_far_above_average";

/**
 * Order on the page. The seven R1 warnings first, strongest first by R2a's
 * explore-period D-U (EXPERIMENT.md, 2026-09-27: spike +0.188, near peak
 * with falling profit +0.153, loss year -0.004, long below peak -0.085
 * with the one-year fall merged into it by R1; the two with no explore
 * cases last), then the situations that are not R1 warnings. An order,
 * never a score: no number is shown for it.
 */
export const WATCH_ORDER: WatchKind[] = [
  "recent_spike",
  "near_ath_earnings_decline",
  "loss_year",
  "fall",
  "long_below_peak",
  "earnings_two_year_decline",
  "yield_far_above_average",
  "recent_price_suspension",
  "repeat_suspension",
  "recent_ipo",
  "earnings_more_than_doubled",
  "payout_above_earnings",
];

export interface WatchItem {
  kind: WatchKind;
  title: string;
  /** What is happening in this stock, as one plain sentence (the section title already names the stock). */
  here: string;
  /** "Dari 100 saham yang ..., <figure> ...": the past frequency, said once. Null when there is none. */
  rate: { lead: string; figure: string; rest: string } | null;
  /** Only what the frequency does not already say about this stock. */
  note: string | null;
  href: string;
}

const WATCH_HREF: Record<WatchKind, string> = {
  ...(Object.fromEntries(Object.entries(SLUG_BY_KIND).map(([k, s]) => [k, `/situasi/${s}`])) as Record<keyof typeof SLUG_BY_KIND, string>),
  payout_above_earnings: "/situasi/dividen-besar",
  near_ath_earnings_decline: "/situasi/dekat-puncak-laba-turun",
  yield_far_above_average: "/temuan/tanda/dividen-tinggi",
};

/** "6 sampai 8" from two rates (of 10), or "7". */
function outOfTen(a: number, b: number): string {
  const lo = Math.round(Math.min(a, b) * 10);
  const hi = Math.round(Math.max(a, b) * 10);
  return lo === hi ? `${lo}` : `${lo} sampai ${hi}`;
}

/** "laba Rp 5,6 M" or "rugi Rp 257 M": rpAmount drops the sign, so the word carries it. */
export function profitWord(v: number): string {
  return `${v < 0 ? "rugi" : "laba"} ${rpAmount(v)}`;
}

/** The rate as one sentence, for places that show it as plain text. */
export function rateSentence(rate: NonNullable<WatchItem["rate"]>): string {
  return `${rate.lead} ${rate.figure} ${rate.rest}`;
}

const BOARD_ID: Record<string, string> = { Acceleration: "Akselerasi", Main: "Utama", Development: "Pengembangan", Watchlist: "Pemantauan Khusus" };

export function watchItems(r: ReadInput): WatchItem[] {
  const { code, situations: s, base, data, profile } = r;
  const price = data.snapshot.last_close_price;
  const flag = (key: string) => data.flags.find((f) => f.key === key);
  const items: Omit<WatchItem, "href">[] = [];
  for (const kind of WATCH_ORDER) {
    switch (kind) {
      case "fall": {
        const f = s?.fall;
        if (!f) break;
        const back = 100 - of100(base.recovery_after_fall.still_below_peak.pct ?? 0);
        const now = price ?? f.last_close;
        items.push({
          kind,
          title: "Turun banyak dalam setahun",
          here: `${formatPrice(now)}, turun ${idNum(Math.abs(pctFrom(now, f.peak_price)), 0)}% dari puncaknya ${formatPrice(f.peak_price)} (${dateLong(f.peak_date)}).`,
          rate: { lead: "Dari 100 saham yang turun 30% atau lebih,", figure: `${back}`, rest: "sudah kembali ke puncaknya setahun kemudian." },
          note: null,
        });
        break;
      }
      case "long_below_peak": {
        const l = s?.long_below_peak;
        if (!l) break;
        const back = of100((base.long_below_peak.recovered_by_504.rate ?? 0) * 100);
        const since = s?.older_fall?.trigger_date;
        const now = price ?? l.last_close;
        items.push({
          kind,
          title: "Lama di bawah puncak",
          here: `Jatuh 30% dari puncak ${formatPrice(l.peak_price)}${since ? ` pada ${dateLong(since)}` : " lebih dari setahun lalu"} dan belum kembali ke sana. Sekarang ${formatPrice(now)}, ${idNum(Math.abs(pctFrom(now, l.peak_price)), 0)}% di bawahnya.`,
          rate: { lead: "Dari 100 saham yang setahun sesudah jatuh masih di bawah puncaknya,", figure: `${back}`, rest: "sudah kembali ke puncak itu dua tahun sesudah jatuh." },
          note: null,
        });
        break;
      }
      case "recent_price_suspension": {
        const x = s?.recent_price_suspension;
        if (!x) break;
        items.push({
          kind,
          title: "Disuspensi karena lonjakan",
          here: `Perdagangannya dihentikan sementara oleh bursa pada ${dateLong(x.date)} karena harganya naik tidak wajar.`,
          rate: { lead: "Dari 100 saham yang disuspensi seperti ini,", figure: `${H11_UNDERPERFORM.holdout}`, rest: "kalah dari IHSG dalam 90 hari sesudahnya." },
          note: null,
        });
        break;
      }
      case "repeat_suspension": {
        const x = s?.repeat_suspension;
        if (!x) break;
        const again = of100(base.repeat_spike_suspension.share_followed * 100);
        items.push({
          kind,
          title: "Langganan suspensi",
          here: `Sudah ${x.n_events} kali disuspensi karena lonjakan harga, ${dateLong(x.first_date)} sampai ${dateLong(x.last_date)}.`,
          rate: { lead: "Dari 100 suspensi karena lonjakan,", figure: `${again}`, rest: "diikuti suspensi serupa dalam setahun." },
          note: null,
        });
        break;
      }
      case "recent_spike": {
        const x = s?.recent_spike;
        if (!x) break;
        const below = of100(base.recent_spike.pooled.share_below_event_close * 100);
        items.push({
          kind,
          title: "Harga baru melonjak",
          here: `Naik ${idNum(x.jump_pct, 0)}% dalam ${x.lookback_trading_days} hari bursa sampai ${dateLong(x.event_date)}.`,
          rate: { lead: "Dari 100 saham yang melonjak seperti ini,", figure: `${below}`, rest: "harganya lebih rendah 60 hari bursa kemudian." },
          note: null,
        });
        break;
      }
      case "loss_year": {
        const x = s?.loss_year;
        if (!x) break;
        const up = of100(base.loss_maker_turnaround.pct ?? 0);
        // The year before is already in the Kesimpulan's Laba row; not repeated here.
        items.push({
          kind,
          title: "Perusahaan rugi",
          here: `Rugi bersih ${rpAmount(x.net_income)} pada ${x.year}.`,
          rate: { lead: "Dari 100 perusahaan rugi,", figure: `${up}`, rest: "kembali untung tahun berikutnya." },
          note: null,
        });
        break;
      }
      case "earnings_two_year_decline": {
        const x = s?.earnings_two_year_decline;
        if (!x) break;
        const up = of100(base.earnings_two_year_decline.pooled.rate * 100);
        const [a, b, c] = x.earnings;
        items.push({
          kind,
          title: "Laba turun dua tahun",
          here: `${profitWord(a).replace(/^./, (ch) => ch.toUpperCase())} pada ${x.year - 2}, ${profitWord(b)} pada ${x.year - 1}, lalu ${profitWord(c)} pada ${x.year}.`,
          rate: { lead: "Dari 100 perusahaan yang labanya turun dua tahun,", figure: `${up}`, rest: "labanya naik lagi tahun berikutnya." },
          note: "Naik lagi belum berarti kembali ke laba semula.",
        });
        break;
      }
      case "recent_ipo": {
        const x = s?.recent_ipo;
        if (!x) break;
        const cell = r.ipo.holdout.horizons["365d"]?.by_board[x.board];
        const tested = (x.board === "Acceleration" || x.board === "Main") && cell;
        const board = BOARD_ID[x.board] ?? x.board;
        items.push({
          kind,
          title: "IPO kurang dari setahun",
          here: `Melantai ${dateLong(x.listing_date)} di Papan ${board}, jadi sebagian perbandingan di halaman ini belum bisa dihitung.`,
          rate: tested ? { lead: `Dari 100 IPO di Papan ${board},`, figure: `${Math.round(cell.negative_rate_pct)}`, rest: "harganya di bawah penutupan hari pertama setahun kemudian." } : null,
          note: tested ? null : `Papan ${board} tidak masuk uji IPO kami.`,
        });
        break;
      }
      case "earnings_more_than_doubled": {
        const x = s?.earnings_more_than_doubled;
        if (!x) break;
        const lowerNext = of100(base.earnings_more_than_doubled.gave_part_back.rate * 100);
        items.push({
          kind,
          title: "Laba lebih dari dua kali lipat",
          here: `Laba naik dari ${rpAmount(x.earnings[0])} pada ${x.year - 1} ke ${rpAmount(x.earnings[1])} pada ${x.year}.`,
          rate: { lead: "Dari 100 perusahaan yang labanya melonjak seperti ini,", figure: `${lowerNext}`, rest: "labanya lebih rendah tahun berikutnya." },
          note: null,
        });
        break;
      }
      case "payout_above_earnings": {
        if (!flag(kind)) break;
        const pr = base.payout_above_100_cut_rate;
        const ratio = payoutOf(r);
        items.push({
          kind,
          title: "Dividen melebihi laba",
          here: ratio !== null && ratio > 1 ? `Membagikan ${payoutWords(ratio)} sebagai dividen.` : "Dividen yang dibayar lebih besar dari labanya.",
          rate: { lead: "Dari 10 perusahaan yang membagikan lebih dari labanya,", figure: outOfTen(pr.explore.cut_rate, pr.holdout.cut_rate), rest: "memangkas dividen tahun berikutnya." },
          note: null,
        });
        break;
      }
      case "yield_far_above_average": {
        const f = flag(kind);
        if (!f) break;
        const yNow = f.detail.yield_ttm as number | undefined;
        const yAvg = f.detail.yield_avg as number | undefined;
        const cut = r.yieldCut;
        items.push({
          kind,
          title: "Imbal dividen jauh di atas rata-ratanya",
          here: yNow !== undefined && yAvg !== undefined ? `Imbal dividen ${pctPlain(yNow)}, padahal rata-rata ${code} sendiri ${pctPlain(yAvg)}.` : "Imbal dividen jauh di atas rata-rata perusahaan ini sendiri.",
          rate: cut.rate === null ? null : { lead: `Dari 100 perusahaan dengan tanda ini (${cut.n} kasus, ${cut.year}),`, figure: `${of100(cut.rate * 100)}`, rest: "memangkas dividen tahun berikutnya." },
          note: "Imbal setinggi ini biasanya karena harganya turun, bukan karena dividennya naik.",
        });
        break;
      }
      case "near_ath_earnings_decline": {
        if (!flag(kind)) break;
        const neg = of100(base.near_peak_earnings_decline.pooled.share_negative * 100);
        items.push({
          kind,
          title: "Dekat puncak, laba turun",
          here: `Harga dalam 10% dari tertinggi sepanjang masa${profile.all_time_high !== null ? ` (${formatPrice(profile.all_time_high)})` : ""}, sementara laba ${r.meta.years[Y.last]} lebih rendah dari ${r.meta.years[Y.prev]}.`,
          rate: { lead: "Dari 100 saham dalam keadaan ini,", figure: `${neg}`, rest: "harganya lebih rendah 4 bulan kemudian." },
          note: null,
        });
        break;
      }
    }
  }
  return items.map((i) => ({ ...i, href: WATCH_HREF[i.kind] }));
}

/* ------------------------------------------------------------------ purpose answers */

export type { Answer, Evidence, Purpose };

/** A situation as one evidence row: this stock's fact, then the past frequency. The card's heading already names the stock. */
function watchEvidence(items: WatchItem[], kinds: WatchKind[]): Evidence[] {
  return items
    .filter((w) => kinds.includes(w.kind) && w.rate)
    .map((w) => ({ text: `${w.here} ${rateSentence(w.rate!)}`, kind: "base" as const, href: w.href }));
}

function tested(r: ReadInput, key: FindingKey, text: string): Evidence {
  return { text, kind: r.findings[key].verdict, href: r.findings[key].href };
}

/** A tested pattern that does not apply to this stock: stated as a fact, no verdict chip beside it. */
function notApplicable(r: ReadInput, key: FindingKey, text: string): Evidence {
  return { text, kind: null, href: r.findings[key].href };
}

export function answers(r: ReadInput, watch: WatchItem[]): Record<Purpose, Answer> {
  const { code, profile: p, meta, data } = r;
  const price = data.snapshot.last_close_price;
  const high = data.snapshot["52_w_high_price"];
  const low = data.snapshot["52_w_low_price"];
  const chg = p.change_1y;
  const e = p.earnings;
  const years = meta.years;
  const last = e[Y.last];
  const prev = e[Y.prev];
  const yoy = last !== null && last >= 0 && prev !== null && prev > 0 ? last / prev - 1 : null;
  const labaLine =
    last !== null && last < 0
      ? `${code} ${prev !== null && prev > 0 ? "berbalik rugi" : "rugi"} ${rpAmount(last)} pada ${years[Y.last]}.`
      : yoy === null
        ? ""
        : `Laba ${code} ${years[Y.last]} ${changeWords(yoy, 0)}.`;
  const vsLine = chg === null ? "" : headline(r).headline;
  const dist = price !== null && high ? pctFrom(price, high) : null;
  const spe = data.sector_context?.sector_typical_pe ?? null;
  const pressured = r.market.state === "tertekan";

  /* turun */
  const turunLead =
    dist === null
      ? `Harga ${code} tidak lengkap, jadi jaraknya dari harga tertinggi setahun tidak bisa dihitung.`
      : dist > -10
        ? `${code} tidak sedang turun jauh: ${signedPct(dist)} dari harga tertinggi setahunnya (${formatPrice(high)}).`
        : `${code} turun ${idNum(Math.abs(dist), 1)}% dari harga tertinggi setahunnya (${formatPrice(high)}${p.w52_high_date ? `, ${dateLong(p.w52_high_date)}` : ""}).`;
  const turunEvidence = [
    ...watchEvidence(watch, ["fall", "long_below_peak"]),
    tested(r, "oversold", `Kalau menurut Anda ${code} sudah "oversold" dan akan memantul: pola RSI di bawah 30 tidak terbukti di data kami.`),
    ...(pressured ? [tested(r, "market_state", `IHSG sedang tertekan, ${pctPlain(r.market.pct_from_peak)} di bawah puncaknya. Pasar tertekan tidak terbukti membuat penurunan lanjutan lebih mungkin.`)] : []),
  ];

  /* murah */
  let murah: Answer;
  if (p.pe_meaningful && p.pe_ttm !== null) {
    const pe = p.pe_ttm;
    const vsSector = isMeaningfulPe(spe) ? (pe < spe * 0.8 ? "lebih rendah dari" : pe > spe * 1.25 ? "lebih tinggi dari" : "setara dengan") : null;
    const range = ownPeRange(p, years);
    const history = range
      ? ` P/E ${code} sendiri di akhir ${range.from} sampai ${years[Y.last]} berkisar ${idNum(range.min)}x sampai ${idNum(range.max)}x, jadi sekarang ${pe < range.min ? "di bawah" : pe > range.max ? "di atas" : "di dalam"} kisaran biasanya.`
      : "";
    const inCheapThird = p.pe_cheaper_than !== null && p.pe_cheaper_than >= TOP_THIRD;
    murah = {
      lead: `P/E ${code} ${idNum(pe)}x${vsSector ? `, ${vsSector} nilai tengah sektornya (${idNum(spe!)}x)` : ""}. Di antara saham berlaba, ${of100(p.pe_cheaper_than ?? 0)}% punya P/E lebih tinggi.`,
      body: `Artinya harga ${code} Rp ${idNum(pe)} untuk tiap Rp 1 laba setahun.${history}`,
      evidence: [
        inCheapThird
          ? tested(r, "low_pe", `P/E rendah ${code} masuk pola yang terbukti memberi hasil sedikit lebih baik, rata-rata ratusan saham. Pengaruhnya kecil.`)
          : notApplicable(r, "low_pe", `P/E ${code} tidak termasuk sepertiga termurah, jadi pola "P/E rendah" yang terbukti itu tidak berlaku di sini.`),
        ...(p.roe_ttm !== null ? [tested(r, "high_roe", `ROE ${code} ${pctPlain(p.roe_ttm)}. ROE tinggi tidak terbukti memprediksi hasil lebih baik.`)] : []),
        ...(p.pb_mrq !== null && p.pb_mrq > 0 ? [{ text: `P/B ${code} ${idNum(p.pb_mrq, 2)}x: harga pasarnya ${p.pb_mrq < 1 ? "di bawah" : "di atas"} nilai buku modal perusahaan.`, kind: null }] : []),
      ],
      check: [...(inCheapThird ? [`P/E rendah bisa berarti pasar memperkirakan laba ${code} turun. Bandingkan dengan laporan laba kuartal berikutnya.`] : []), `Bandingkan ${code} dengan ${sectorStocks(r)} lain, bukan dengan seluruh pasar.`],
    };
  } else {
    murah = {
      lead: {
        loss: `${code} tidak punya P/E yang bermakna: rugi pada ${years[Y.last]}.`,
        near_zero: `${code} tidak punya P/E yang bermakna: labanya hampir nol.`,
        missing: `P/E ${code} tidak tercatat di data kami.`,
      }[peMissingReason(p)],
      body: `${peMissingReason(p) === "missing" ? "Tanpa P/E, murah atau mahal tidak bisa diukur dari laba." : "Tanpa laba, murah atau mahal tidak bisa diukur dari P/E."}${p.pb_mrq !== null && p.pb_mrq > 0 ? ` P/B ${code} ${idNum(p.pb_mrq, 2)}x: harga Rp ${idNum(p.pb_mrq, 2)} untuk tiap Rp 1 modal.` : ""}`,
      evidence: [notApplicable(r, "low_pe", `Pola "P/E rendah memberi hasil lebih baik" butuh P/E yang bermakna, jadi tidak bisa dipakai untuk ${code} sekarang.`)],
      check: [`Bagaimana laba ${code} lima tahun terakhir? Lihat grafik di bagian Laba ${code}.`],
    };
  }

  /* dividen */
  const d = p.dividend;
  const dShape = dividendShape(d);
  const dLast = d[Y.last];
  const yieldNow = p.yield_ttm;
  let dividen: Answer;
  if (dShape === "never") {
    dividen = {
      lead: `${code} tidak membagikan dividen dari ${years[0]} sampai ${years[Y.last]}.`,
      body: (last ?? 0) < 0 ? "Perusahaan rugi umumnya tidak membagikan dividen." : `Laba yang ada ditahan perusahaan, tidak dibagikan.`,
      evidence: [notApplicable(r, "high_yield", `Pola "dividen tinggi memberi hasil lebih baik" tidak berlaku untuk ${code}, karena tidak ada dividen.`)],
      check: [],
    };
  } else {
    const payout = payoutOf(r);
    const history: Record<DividendShape, string> = {
      never: "",
      every_year_falling: `Dibayar setiap tahun sejak ${years[0]}, tapi turun dua tahun berturut-turut.`,
      every_year_rising: `Dibayar setiap tahun sejak ${years[0]}, dan naik pada ${years[Y.last]}.`,
      every_year: `Dibayar setiap tahun sejak ${years[0]}.`,
      first_time: `Ini dividen pertama dalam data ${years[0]} sampai ${years[Y.last]}.`,
      not_every_year: `Tidak dibayar setiap tahun: ${years.filter((_, i) => d[i] !== null && (d[i] as number) > 0).join(", ")}.`,
      skipped_latest: `Terakhir dibayar untuk ${years.filter((_, i) => d[i] !== null && (d[i] as number) > 0).pop()}.`,
    };
    const payoutFlag = watch.find((w) => w.kind === "payout_above_earnings");
    dividen = {
      lead:
        dLast !== null && dLast > 0
          ? `${code} membagikan Rp ${idNum(dLast, dLast < 10 ? 2 : 0)} per saham untuk ${years[Y.last]}.${yieldNow !== null && yieldNow > 0 ? ` Imbal 12 bulan terakhir ${pctPlain(yieldNow)} dari harga sekarang.` : ""}`
          : `${code} tidak membagikan dividen untuk ${years[Y.last]}.`,
      body: `${yieldNow !== null && yieldNow > 0 ? `Imbal itu lebih tinggi dari ${of100(p.yield_higher_than)}% saham. ` : ""}${history[dShape]}${payout !== null && payout > 0 ? ` ${code} membagikan ${payoutWords(payout)}.` : ""}`,
      evidence: [
        isHighYield(p)
          ? tested(r, "high_yield", `Dividen ${code} termasuk sepertiga tertinggi di antara pembayar dividen. Saham berdividen tinggi terbukti memberi hasil sedikit lebih baik, rata-rata.`)
          : notApplicable(
              r,
              "high_yield",
              yieldNow !== null && yieldNow > 0
                ? `Dividen ${code} tidak termasuk sepertiga tertinggi di antara pembayar dividen, jadi pola "dividen tinggi" yang terbukti itu tidak berlaku di sini.`
                : `Tidak ada dividen ${code} dalam 12 bulan terakhir, jadi pola "dividen tinggi" yang terbukti itu tidak berlaku di sini.`
            ),
        ...(payoutFlag
          ? watchEvidence(watch, ["payout_above_earnings"])
          : payout !== null && payout > 0 && payout <= 1
            ? [{ text: `${code} membagikan ${idNum(payout * 100, 0)}% dari labanya, di bawah 100%. Yang membagikan lebih dari labanya memangkas dividen ${outOfTen(r.base.payout_above_100_cut_rate.explore.cut_rate, r.base.payout_above_100_cut_rate.holdout.cut_rate)} dari 10 kali; ${code} tidak termasuk.`, kind: "base" as const }]
            : []),
        ...watchEvidence(watch, ["yield_far_above_average"]),
      ],
      check: [`Imbal dihitung dari dividen 12 bulan terakhir. Dividen ${code} tahun ini bisa berbeda.`, `Tanggal ex dividen ${code} berikutnya ada di Data lengkap, bagian Aksi korporasi.`],
    };
  }

  /* tip */
  const ins = data.insider_activity;
  const n = r.news;
  const tipEvidence: Evidence[] = [];
  if (ins) tipEvidence.push(tested(r, "insider_buy", `"Orang dalam ${code} borong": tercatat ${ins.buy_count} laporan beli dan ${ins.sell_count} jual sejak ${dateLong(r.insiderSince)}. Pembelian orang dalam tidak terbukti menaikkan harga.`));
  tipEvidence.push(
    tested(
      r,
      "foreign_buy",
      `"Asing mulai masuk ${code}": ${code} di daftar beli bersih asing ${p.foreign_buy_days} hari dan jual bersih ${p.foreign_sell_days} hari dari ${meta.foreign_flow.days} hari. Pola asing borong tidak terbukti.`
    )
  );
  if (n && n.bullish + n.bearish > 0) tipEvidence.push(tested(r, "news_tone", `"Berita ${code} bagus": ${n.bullish} artikel positif, ${n.bearish} negatif. Nada berita belum terbukti memprediksi harga.`));
  if (yieldNow !== null && yieldNow > 0)
    tipEvidence.push(
      isHighYield(p)
        ? tested(r, "high_yield", `"Dividen ${code} besar": benar, imbal ${pctPlain(yieldNow)}, sepertiga tertinggi di antara pembayar dividen. Dividen tinggi terbukti memberi hasil sedikit lebih baik, rata-rata.`)
        : notApplicable(r, "high_yield", `"Dividen ${code} besar": imbal ${pctPlain(yieldNow)}, tidak termasuk sepertiga tertinggi di antara pembayar dividen.`)
    );
  const tip: Answer = {
    lead: `Tempel pesannya, kami cocokkan tiap klaim dengan data ${code}.`,
    body: `Klaim yang paling sering muncul di pesan tentang saham seperti ${code} sudah kami periksa di bawah.`,
    evidence: tipEvidence,
    check: [`Target harga ${code} di pesan tidak bisa kami periksa. Tanyakan pengirimnya dari mana angka itu.`],
    paste: true,
  };

  /* naik */
  const spike = r.situations?.recent_spike;
  const suspended = r.situations?.recent_price_suspension;
  const rising = Boolean(spike) || (chg !== null && chg > 0) || (chg === null && price !== null && low !== null && price > low * 1.3);
  const naikLead = spike
    ? `${code} naik ${idNum(spike.jump_pct, 0)}% dalam ${spike.lookback_trading_days} hari bursa sampai ${dateLong(spike.event_date)}.${suspended ? " Lalu perdagangannya dihentikan sementara oleh bursa." : ""}`
    : chg !== null && chg > 0
      ? `${code} ${changeWords(chg)} dalam setahun, saat IHSG ${changeWords(meta.ihsg_change_1y)}.`
      : chg === null && price !== null && low
        ? `${code} ${changeWords(pctFrom(price, low) / 100)} dari harga terendah setahunnya (${formatPrice(low)}${p.w52_low_date ? `, ${dateLong(p.w52_low_date)}` : ""})${dist !== null ? `, dan ${idNum(Math.abs(dist), 1)}% di bawah tertingginya` : ""}.`
        : `${code} tidak sedang naik tinggi: ${chg !== null ? `${changeWords(chg)} dalam setahun` : "perubahan setahun tidak tersedia"}${dist !== null ? `, ${idNum(Math.abs(dist), 1)}% di bawah tertinggi setahun` : ""}.`;
  const peLine = p.pe_meaningful && p.pe_ttm !== null ? ` Harga ${code} sekarang ${idNum(p.pe_ttm, 0)} kali laba setahun${isMeaningfulPe(spe) ? `, nilai tengah sektornya ${idNum(spe, 0)} kali` : ""}.` : "";
  const naik: Answer = {
    lead: naikLead,
    body: `${labaLine}${peLine}`.trim() || vsLine,
    evidence: [
      ...watchEvidence(watch, ["recent_spike", "recent_price_suspension", "repeat_suspension"]),
      tested(r, "top_gainer", `Kalau Anda berharap ${code} terus naik karena naiknya tinggi: saham yang naik paling tinggi tidak terbukti terus naik sebulan sesudahnya.`),
      tested(r, "momentum", `Tren 60 hari tidak terbukti memprediksi arah bulan berikutnya.`),
    ],
    check: [
      ...(suspended ? [`Selama suspensi ${code} tidak bisa diperdagangkan. Cek pengumuman IDX untuk tanggal dibuka kembali.`] : []),
      rising ? `Apakah ada berita perusahaan yang menjelaskan kenaikan ${code}? Lihat Data lengkap, bagian Berita.` : `Kalau yang Anda lihat kenaikan satu hari, bandingkan dengan pergerakan setahun di bagian Harga ${code}.`,
    ],
  };

  return {
    turun: {
      lead: turunLead,
      body: [p.change_1y === null ? "" : headline(r).headline, pressured ? `IHSG sendiri sedang tertekan: ${pctPlain(r.market.pct_from_peak)} di bawah puncaknya.` : "", labaLine].filter(Boolean).join(" "),
      evidence: turunEvidence,
      check: [`Laporan laba kuartal berikutnya: apakah laba ${code} ikut turun?`, `Apakah ${code} tetap membagikan dividen tahun ini?`],
    },
    murah,
    dividen,
    tip,
    naik,
  };
}

/* ------------------------------------------------------------------ Tanya suggestions */

export function tanyaSuggestions(r: ReadInput): string[] {
  const { code, profile: p } = r;
  const shape = earningsShape(p.earnings);
  const chg = p.change_1y;
  let first: string;
  if (shape.startsWith("loss") || shape === "turned_loss") first = `Kapan ${code} terakhir untung?`;
  else if (chg !== null && chg < -0.05 && ["rising_every_year", "up", "stable", "stable_near_high"].includes(shape)) first = `Kenapa ${code} turun padahal labanya ${shape === "up" || shape === "rising_every_year" ? "naik" : "stabil"}?`;
  else if (chg !== null && chg > 0.5) first = `Kenapa ${code} naik tinggi setahun ini?`;
  else first = `Jelaskan ${code} dengan bahasa sederhana`;
  const second = dividendShape(p.dividend) === "never" ? `Bagaimana laba ${code} lima tahun terakhir?` : `Bagaimana dividen ${code} lima tahun terakhir?`;
  return [first, second];
}

/* ------------------------------------------------------------------ Pantau */

export interface AgendaItem {
  date: string;
  label: string;
  past: boolean;
}

/** Dated events for the Pantau card, newest first, at most four. */
export function agenda(r: ReadInput): AgendaItem[] {
  const { data, situations: s } = r;
  const ca = data.corporate_actions;
  const ref = ca.as_of;
  const items: AgendaItem[] = [];
  for (const d of ca.dividends) {
    items.push({ date: d.ex_date, label: `Ex dividen${d.amount !== null ? ` ${formatPrice(d.amount)}` : ""}`, past: d.ex_date <= ref });
    if (d.payment_date) items.push({ date: d.payment_date, label: `Pembayaran dividen${d.amount !== null ? ` ${formatPrice(d.amount)}` : ""}`, past: d.payment_date <= ref });
  }
  for (const a of ca.agms) items.push({ date: a.agm_date, label: a.cancelled ? "RUPS (tercatat dibatalkan)" : "RUPS", past: a.agm_date <= ref });
  for (const x of ca.rights_issues) items.push({ date: x.ex_date, label: "Ex penawaran saham baru (rights issue)", past: x.ex_date <= ref });
  for (const x of ca.stock_splits) items.push({ date: x.date, label: `Pemecahan saham${x.ratio ? ` ${x.ratio}` : ""}`, past: x.date <= ref });
  if (s?.recent_price_suspension) items.push({ date: s.recent_price_suspension.date, label: "Suspensi oleh bursa", past: true });
  if (data.insider_activity?.last_transaction_date) items.push({ date: data.insider_activity.last_transaction_date, label: "Laporan transaksi orang dalam terakhir", past: true });
  return items.sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 4);
}

/* ------------------------------------------------------------------ card lines */

/** Harga card: where today's price sits in the one-year range. */
export function hargaLine(r: ReadInput): string | null {
  const { snapshot } = r.data;
  const price = snapshot.last_close_price;
  const low = snapshot["52_w_low_price"];
  const high = snapshot["52_w_high_price"];
  if (price === null || low === null || high === null || high <= low) return null;
  const dist = signedPct(pctFrom(price, high));
  if (price <= low) return `Harga sekarang sama dengan terendah setahun: ${dist} dari tertinggi setahun.`;
  if (price >= high) return "Harga sekarang sama dengan tertinggi setahun.";
  const pos = (price - low) / (high - low);
  const part = pos < 1 / 3 ? "bawah" : pos < 2 / 3 ? "tengah" : "atas";
  const wide = high >= 3 * low ? ` Rentangnya lebar: tertinggi ${idNum(high / low, 0)} kali terendahnya.` : "";
  return `Harga sekarang di bagian ${part} rentang setahun: ${dist} dari tertinggi setahun.${wide}`;
}

/** Laba card: the five-year path in one sentence. */
export function labaSeriesLine(r: ReadInput): string | null {
  const e = r.profile.earnings;
  const years = r.meta.years;
  const known = e.map((v, i) => ({ v, y: years[i] })).filter((x): x is { v: number; y: number } => x.v !== null);
  if (known.length < 2) return null;
  const losses = known.filter((x) => x.v < 0);
  const first = known[0];
  const last = known[known.length - 1];
  if (losses.length === 0) {
    const change = last.v / first.v - 1;
    return `Dari ${rpAmount(first.v)} (${first.y}) ke ${rpAmount(last.v)} (${last.y}): ${change >= 0 ? "naik" : "turun"} ${pctPlain(change, 0)} dalam ${last.y - first.y} tahun.`;
  }
  if (losses.length === known.length) {
    const worst = losses.reduce((a, b) => (b.v < a.v ? b : a));
    return `Rugi setiap tahun sejak ${first.y}. Rugi terbesar pada ${worst.y} (${rpAmount(worst.v)}).`;
  }
  return `Rugi pada ${losses.map((x) => x.y).join(", ")}; untung pada ${known.filter((x) => x.v >= 0).map((x) => x.y).join(", ")}.`;
}

/** ROE in plain words, against the sector's typical value. */
export function roeLine(r: ReadInput): string | null {
  const roe = r.profile.roe_ttm;
  if (roe === null) return null;
  const sector = r.data.sector_context?.sector_typical_roe_pct ?? null;
  const vs = sector !== null && r.sector ? ` Nilai tengah sektor ${lower(r.sector)} ${idNum(sector)}%.` : "";
  if (roe < 0) return `ROE ${signedPct(roe * 100)}: modal perusahaan berkurang karena rugi.${vs}`;
  return `ROE ${pctPlain(roe)}: setiap Rp 100 modal menghasilkan Rp ${idNum(roe * 100, 0)} laba setahun.${vs}`;
}

/** Dividen card: how often and how much of the profit. */
export function dividenLine(r: ReadInput): string {
  const d = r.profile.dividend;
  const years = r.meta.years;
  const payout = payoutOf(r);
  const paid = years.filter((_, i) => d[i] !== null && (d[i] as number) > 0);
  const shape = dividendShape(d);
  const how =
    shape === "never"
      ? `Tidak ada dividen tercatat dari ${years[0]} sampai ${years[Y.last]}.`
      : shape.startsWith("every_year")
        ? `Dibayar setiap tahun sejak ${years[0]}.`
        : shape === "first_time"
          ? `Dividen pertama dalam data ini dibagikan untuk tahun ${paid[0]}.`
          : `Dibayar untuk ${paid.join(", ")}.`;
  const share = payout !== null && payout > 0 && shape !== "never" ? ` Perusahaan membagikan ${payoutWords(payout)}.` : "";
  return `${how}${share}`;
}

/** "Perusahaan terbesar ke-11 dari 962 di bursa, nilai pasar Rp 198,8 T." */
export function sizeLine(r: ReadInput): string | null {
  const { market_cap, market_cap_rank } = r.data.snapshot;
  if (market_cap === null || market_cap_rank === null) return null;
  return `Perusahaan terbesar ke-${market_cap_rank} dari ${r.universe} di bursa, nilai pasar ${rpAmount(market_cap)}.`;
}
