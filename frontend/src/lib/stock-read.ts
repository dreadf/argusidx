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
 * Ringkasan rows, the popular signals present in the stock with their test
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

/** Share of 100 as a quantifier: 12 -> "sedikit", 57 -> "lebih dari separuh". */
export function quantifier(outOf100: number): string {
  if (outOf100 < 20) return "sedikit";
  if (outOf100 < 45) return "kurang dari separuh";
  if (outOf100 <= 55) return "sekitar separuh";
  if (outOf100 < 80) return "lebih dari separuh";
  return "sebagian besar";
}

const of100 = (share: number) => Math.round(share);
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

/* ------------------------------------------------------------------ price relation */

type PriceRelation = { dir: "Naik" | "Turun"; rel: string };

function priceRelation(chg: number, ihsg: number): PriceRelation {
  const dir = chg >= 0 ? "Naik" : "Turun";
  const diff = chg - ihsg;
  let rel: string;
  if (Math.abs(diff) <= 0.03) rel = "sejalan dengan IHSG";
  else if (chg < 0) rel = diff > 0 ? "lebih ringan dari IHSG" : "lebih dalam dari IHSG";
  else if (ihsg < 0) rel = "saat IHSG turun";
  else rel = diff > 0 ? "lebih tinggi dari IHSG" : "lebih rendah dari IHSG";
  return { dir, rel };
}

/* ------------------------------------------------------------------ Ringkasan */

export interface RingkasanRow {
  label: string;
  state: string;
  explain: string;
}

export interface Ringkasan {
  lead: string;
  rows: RingkasanRow[];
}

function hargaRow(r: ReadInput): RingkasanRow {
  const { profile, meta, data } = r;
  const chg = profile.change_1y;
  const price = data.snapshot.last_close_price;
  const low = data.snapshot["52_w_low_price"];
  const high = data.snapshot["52_w_high_price"];
  const ipo = r.situations?.recent_ipo;
  if (chg === null) {
    const dist = price !== null && high ? `${signedPct(pctFrom(price, high))} dari tertinggi setahun.` : "";
    return ipo
      ? { label: "Harga", state: "Belum setahun di bursa", explain: `Melantai ${dateLong(ipo.listing_date)}, jadi perubahan setahun belum bisa dihitung. ${dist}`.trim() }
      : { label: "Harga", state: "Perubahan setahun tidak tersedia", explain: dist || "Harga awal periode tidak tercatat." };
  }
  const { dir, rel } = priceRelation(chg, meta.ihsg_change_1y);
  let state = chg >= 1 ? "Naik lebih dari dua kali lipat" : `${dir}, ${rel}`;
  if (price !== null && low !== null && high !== null && high > low) {
    if (price <= low) state = "Di harga terendah setahun";
    else if (price >= high) state = "Di harga tertinggi setahun";
    else if (chg < 0 && price <= low * 1.05) state = "Turun, dekat harga terendah setahun";
    else if (chg > 0 && price >= high * 0.95) state = chg >= 1 ? "Naik jauh, dekat harga tertinggi setahun" : "Naik, dekat harga tertinggi setahun";
  }
  const rank = profile.sector_rank_1y;
  let peers = "";
  if (rank && rank.n > 1) peers = rank.better === 0 ? ` Tidak ada ${sectorStocks(r)} lain yang bergerak lebih baik.` : ` ${rank.better} dari ${rank.n} ${sectorStocks(r)} bergerak lebih baik.`;
  return { label: "Harga", state, explain: `${pctSigned(chg)} dalam setahun, IHSG ${pctSigned(meta.ihsg_change_1y)}.${peers}` };
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
    return `, ${yoy >= 0 ? "naik" : "turun"} ${pctPlain(yoy, 0)} dari ${years[Y.prev]}`;
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

function leadSentence(r: ReadInput): string {
  const { code, profile, meta } = r;
  const e = profile.earnings;
  const years = meta.years;
  const allDividends = dividendShape(profile.dividend).startsWith("every_year");
  const divClause = allDividends ? `, dan dividennya dibayar setiap tahun sejak ${years[0]}` : "";
  let biz: string;
  switch (earningsShape(e)) {
    case "loss_shrinking": {
      const two = e[Y.prev2] !== null && (e[Y.prev2] as number) < 0 && Math.abs(e[Y.prev] as number) < Math.abs(e[Y.prev2] as number);
      biz = `${code} masih rugi, tapi ruginya menyusut ${two ? "dua tahun berturut-turut" : `dari ${years[Y.prev]}`}.`;
      break;
    }
    case "loss_growing":
      biz = `${code} masih rugi, dan ruginya membesar pada ${years[Y.last]}.`;
      break;
    case "loss":
      biz = `${code} rugi pada ${years[Y.last]}.`;
      break;
    case "turned_loss":
      biz = `${code} berbalik rugi pada ${years[Y.last]}.`;
      break;
    case "back_to_profit":
      biz = `${code} kembali untung pada ${years[Y.last]} setelah rugi${divClause}.`;
      break;
    case "rising_every_year":
      biz = `Laba ${code} naik setiap tahun sejak ${risingSince(e, years)}${divClause}.`;
      break;
    case "falling_two_years":
      biz = `Laba ${code} turun dua tahun berturut-turut${divClause}.`;
      break;
    case "stable_near_high":
      biz = `Laba ${code} stabil di dekat tertinggi lima tahunnya${divClause}.`;
      break;
    case "stable":
      biz = `Laba ${code} stabil${divClause}.`;
      break;
    case "up":
    case "down": {
      const yoy = (e[Y.last] as number) / (e[Y.prev] as number) - 1;
      biz = `Laba ${code} ${years[Y.last]} ${yoy >= 0 ? "naik" : "turun"} ${pctPlain(yoy, 0)}${divClause}.`;
      break;
    }
    case "none":
      biz = `${code} belum punya laporan laba ${years[Y.last]}.`;
      break;
    default:
      biz = `${code} untung pada ${years[Y.last]}${divClause}.`;
  }
  const chg = profile.change_1y;
  let price: string;
  if (chg === null) {
    const ipo = r.situations?.recent_ipo;
    price = ipo ? `Baru melantai ${dateLong(ipo.listing_date)}, jadi perubahan harga setahun belum bisa dihitung.` : "Perubahan harga setahun tidak tersedia.";
  } else {
    const { dir, rel } = priceRelation(chg, meta.ihsg_change_1y);
    const rank = profile.sector_rank_1y;
    let peers = "";
    if (rank && rank.n >= 5) {
      const share = rank.better / rank.n;
      if (share >= 2 / 3) peers = `, tapi lebih lemah dari kebanyakan ${sectorStocks(r)}`;
      else if (share <= 1 / 3) peers = `, dan lebih kuat dari kebanyakan ${sectorStocks(r)}`;
    }
    price = `Harganya ${dir.toLowerCase()} ${pctPlain(chg)} dalam setahun, ${rel}${peers}.`;
  }
  return `${biz} ${price}`;
}

export function ringkasan(r: ReadInput, watch: WatchItem[]): Ringkasan {
  const rows = [hargaRow(r), labaRow(r), valuasiRow(r), dividenRow(r)];
  rows.push({
    label: "Perlu diperhatikan",
    // Named one by one, never counted: CLAUDE.md allows a count of risk signs only after a confirmed holdout test.
    state: watch.length === 0 ? "Tidak ada" : watch.map((w) => w.title).join(", "),
    explain: watch.length === 0 ? `Tidak ada keadaan khusus yang sedang terjadi di ${r.code}.` : "Setiap hal berdiri sendiri; rinciannya ada di bagian di bawah.",
  });
  return { lead: leadSentence(r), rows };
}

/* ------------------------------------------------------------------ Sinyal populer */

export interface Signal {
  key: SignalKey;
  title: string;
  /** "Di ASII:" line. */
  here: string;
  /** "Hasil uji:" line. */
  result: string;
  verdict: Verdict;
  /** "Artinya untuk ASII:" line. */
  meaning: string;
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
    const usual = range && p.pe_ttm >= range.min * 0.9 ? ` P/E ${code} di akhir ${range.from} sampai ${years[Y.last]} berkisar ${idNum(range.min)}x sampai ${idNum(range.max)}x, jadi rendahnya bukan hal baru.` : "";
    out.push({
      key: "low_pe",
      title: `P/E ${code} rendah`,
      here: `P/E ${idNum(p.pe_ttm)}x, lebih rendah dari ${of100(p.pe_cheaper_than)} dari 100 saham berlaba.${isMeaningfulPe(spe) ? ` Nilai tengah sektornya ${idNum(spe)}x.` : ""}`,
      meaning: `P/E ${code} masuk pola yang terbukti, tapi efeknya kecil dan berlaku rata-rata, bukan untuk satu saham.${usual}`,
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
      here: `Imbal dividen ${pctPlain(p.yield_ttm)}, lebih tinggi dari ${of100(p.yield_higher_than)} dari 100 saham.`,
      meaning: `${code} masuk kelompok berdividen tinggi. Imbal ini dihitung dari dividen 12 bulan terakhir, bukan janji dividen berikutnya.${why}`,
    });
  }
  if (p.size_third === "small" && data.snapshot.market_cap !== null && data.snapshot.market_cap_rank !== null) {
    out.push({
      key: "small",
      title: `${code} perusahaan kecil`,
      here: `Nilai pasar ${rpAmount(data.snapshot.market_cap)}, peringkat ke-${data.snapshot.market_cap_rank} dari ${r.universe}.`,
      meaning: `${code} masuk sepertiga perusahaan terkecil. Keunggulan kelompok ini kecil dan berlaku rata-rata, bukan untuk satu saham.`,
    });
  }
  if (p.roe_ttm !== null && p.roe_ttm > 0 && p.roe_higher_than !== null && p.roe_higher_than >= TOP_THIRD) {
    out.push({
      key: "high_roe",
      title: `ROE ${code} tinggi`,
      here: `ROE ${pctPlain(p.roe_ttm)}: setiap Rp 100 modal menghasilkan Rp ${idNum(p.roe_ttm * 100, 0)} laba setahun. Lebih tinggi dari ${of100(p.roe_higher_than)} dari 100 saham.`,
      meaning: `ROE tinggi ${code} belum bisa dibaca sebagai tanda harganya akan lebih baik.`,
    });
  }
  if (p.der_mrq !== null && p.der_higher_than !== null && p.der_higher_than >= TOP_THIRD) {
    out.push({
      key: "high_debt",
      title: `Utang ${code} tinggi`,
      here: `Utang ${idNum(p.der_mrq, 2)}x modal, lebih tinggi dari ${of100(p.der_higher_than)} dari 100 perusahaan non-keuangan.`,
      meaning: `utang tinggi ${code} belum bisa dibaca sebagai tanda harganya akan lebih buruk.`,
    });
  }
  if (p.revenue_growth !== null && p.revenue_growth > 0 && p.revenue_growth_higher_than !== null && p.revenue_growth_higher_than >= TOP_THIRD) {
    out.push({
      key: "fast_revenue",
      title: `Pendapatan ${code} tumbuh cepat`,
      here: `Pendapatan ${years[Y.last]} naik ${pctPlain(p.revenue_growth)} dari ${years[Y.prev]}, lebih cepat dari ${of100(p.revenue_growth_higher_than)} dari 100 perusahaan.`,
      meaning: `pertumbuhan pendapatan ${code} belum bisa dibaca sebagai tanda harganya akan naik.`,
    });
  }
  const last = e[Y.last];
  const prev = e[Y.prev];
  if (last !== null && prev !== null && prev > 0 && last > prev) {
    const yoy = last / prev - 1;
    const chg = p.change_1y;
    const vsPrice = chg === null ? "" : ` Dalam setahun harganya ${chg >= 0 ? "naik" : "turun"} ${pctPlain(chg)}.`;
    out.push({
      key: "earnings_up",
      title: `Laba ${code} naik`,
      here: `Laba ${years[Y.last]} ${rpAmount(last)}, naik ${pctPlain(yoy, 0)} dari ${years[Y.prev]}.`,
      meaning: `kenaikan laba ${code} belum bisa dibaca sebagai tanda harganya akan naik.${vsPrice}`,
    });
  }
  if (p.foreign_buy_days >= 10 && p.foreign_buy_days >= 1.5 * p.foreign_sell_days) {
    out.push({
      key: "foreign_buy",
      title: `Asing sering membeli ${code}`,
      here: `Di daftar beli bersih asing ${p.foreign_buy_days} hari, daftar jual bersih ${p.foreign_sell_days} hari (dari ${meta.foreign_flow.days} hari).`,
      meaning: `seringnya ${code} muncul di daftar beli asing belum bisa dibaca sebagai tanda harganya akan naik.`,
    });
  }
  const ins = data.insider_activity;
  if (ins && ins.net_direction === "net_buying") {
    out.push({
      key: "insider_buy",
      title: `Orang dalam ${code} membeli`,
      here: `${ins.buy_count} laporan beli, ${ins.sell_count} jual sejak ${dateLong(r.insiderSince)}${ins.last_transaction_date ? `, terakhir ${dateLong(ins.last_transaction_date)}` : ""}.`,
      meaning: `pembelian orang dalam ${code} belum bisa dibaca sebagai tanda harganya akan naik.`,
    });
  }
  const n = r.news;
  if (n && n.bullish + n.bearish >= 20 && n.bullish !== n.bearish) {
    const pos = n.bullish > n.bearish;
    const share = (n.bullish / (n.bullish + n.bearish)) * 100;
    out.push({
      key: "news_tone",
      title: `Berita tentang ${code} lebih banyak ${pos ? "positif" : "negatif"}`,
      here: `${n.bullish} artikel bernada positif, ${n.bearish} negatif (${idNum(share, 0)}% positif; semua saham ${idNum(r.newsMarket.bullishPct, 0)}%), ${dateLong(r.newsMarket.first)} sampai ${dateLong(r.newsMarket.last)}. Label nada dari Sectors.`,
      meaning: `banyaknya berita ${pos ? "positif" : "negatif"} tentang ${code} belum bisa dijadikan petunjuk arah harganya.`,
    });
  }
  if (data.h1_finding?.free_float_tercile === "low" && data.snapshot.free_float !== null) {
    out.push({
      key: "thin_float",
      title: `Free float ${code} kecil`,
      here: `Free float ${idNum(data.snapshot.free_float * 100)}%, sepertiga tersempit untuk ukuran perusahaannya.`,
      meaning: `float kecil ${code} tidak berarti harganya lebih liar. Di data kami, saham float kecil justru rata-rata lebih tenang.`,
    });
  }
  const gain = p.daily_close_change;
  if (p.daily_gain_rank !== null && p.daily_gain_rank <= 10 && gain !== null && gain > 0) {
    out.push({
      key: "top_gainer",
      title: `${code} naik paling tinggi hari ini`,
      here: `Naik ${pctPlain(gain)} pada ${dateLong(meta.as_of)}, peringkat ${p.daily_gain_rank} dari ${r.gainRankCount} saham.`,
      meaning: `kenaikan besar ${code} hari ini belum bisa dibaca sebagai tanda kenaikannya berlanjut.`,
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

export const WATCH_ORDER: WatchKind[] = [
  "fall",
  "long_below_peak",
  "recent_price_suspension",
  "repeat_suspension",
  "recent_spike",
  "loss_year",
  "earnings_two_year_decline",
  "recent_ipo",
  "earnings_more_than_doubled",
  "payout_above_earnings",
  "yield_far_above_average",
  "near_ath_earnings_decline",
];

export interface WatchItem {
  kind: WatchKind;
  title: string;
  /** "Di ASII:" line. */
  here: string;
  /** "Pada saham lain:" line: the bold figure and the rest of the sentence; null when there is no frequency. */
  others: { figure: string; rest: string } | null;
  meaning: string;
  href: string;
}

const WATCH_HREF: Record<WatchKind, string> = {
  ...(Object.fromEntries(Object.entries(SLUG_BY_KIND).map(([k, s]) => [k, `/situasi/${s}`])) as Record<keyof typeof SLUG_BY_KIND, string>),
  payout_above_earnings: "/situasi/dividen-besar",
  near_ath_earnings_decline: "/situasi/dekat-puncak-laba-turun",
  yield_far_above_average: "/temuan/tanda/dividen-tinggi",
};

/** "6 sampai 8 dari 10" from two rates, or "7 dari 10". */
function outOfTen(a: number, b: number): string {
  const lo = Math.round(Math.min(a, b) * 10);
  const hi = Math.round(Math.max(a, b) * 10);
  return lo === hi ? `${lo} dari 10` : `${lo} sampai ${hi} dari 10`;
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
        const below = of100(base.recovery_after_fall.still_below_peak.pct ?? 0);
        const now = price ?? f.last_close;
        items.push({
          kind,
          title: "Turun banyak dalam setahun",
          here: `${formatPrice(now)} sekarang, ${idNum(Math.abs(pctFrom(now, f.peak_price)), 0)}% di bawah puncak ${formatPrice(f.peak_price)} (${dateLong(f.peak_date)}).`,
          others: { figure: `${below} dari 100`, rest: "saham yang turun 30% atau lebih belum kembali ke puncaknya setahun kemudian." },
          meaning: `kembali ke ${formatPrice(f.peak_price)} dalam setahun terjadi pada ${quantifier(100 - below)} saham yang turun sedalam ${code}.`,
        });
        break;
      }
      case "long_below_peak": {
        const l = s?.long_below_peak;
        if (!l) break;
        const back = of100((base.long_below_peak.recovered_by_504.rate ?? 0) * 100);
        const peakDate = s?.older_fall?.peak_date;
        const now = price ?? l.last_close;
        items.push({
          kind,
          title: "Lama di bawah puncak",
          here: `${formatPrice(now)} sekarang, ${idNum(Math.abs(pctFrom(now, l.peak_price)), 0)}% di bawah puncak ${formatPrice(l.peak_price)}${peakDate ? ` (${dateLong(peakDate)})` : ""}, sudah ${idNum(l.trading_days_since_trigger, 0)} hari bursa sejak jatuh 30%.`,
          others: { figure: `${back} dari 100`, rest: "saham yang lama di bawah puncaknya kembali ke puncak itu setahun kemudian." },
          meaning: `kembalinya ${code} ke ${formatPrice(l.peak_price)} dalam setahun terjadi pada ${quantifier(back)} saham dalam keadaan serupa.`,
        });
        break;
      }
      case "recent_price_suspension": {
        const x = s?.recent_price_suspension;
        if (!x) break;
        items.push({
          kind,
          title: "Disuspensi karena lonjakan",
          here: `Disuspensi bursa ${dateLong(x.date)}, ${x.days_ago} hari sebelum data ini.`,
          others: { figure: `${H11_UNDERPERFORM.holdout} dari 100`, rest: "saham kalah dari indeks dalam 90 hari setelah suspensi seperti ini." },
          meaning: `hasil sesudah suspensi seperti di ${code} terbelah: sebagian terus naik, tapi lebih banyak yang tertinggal dari indeks.`,
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
          here: `${x.n_events} kali disuspensi karena lonjakan, ${dateLong(x.first_date)} sampai ${dateLong(x.last_date)}.`,
          others: { figure: `${again} dari 100`, rest: "suspensi karena lonjakan diikuti suspensi serupa dalam setahun." },
          meaning: `suspensi berulang terjadi pada ${quantifier(again)} kasus serupa, dan ${code} sudah ${x.n_events} kali.`,
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
          others: { figure: `${below} dari 100`, rest: "saham yang melonjak seperti ini berada di harga lebih rendah 60 hari bursa kemudian." },
          meaning: `${quantifier(below)} saham yang melonjak seperti ${code} berada di harga lebih rendah 60 hari bursa kemudian.`,
        });
        break;
      }
      case "loss_year": {
        const x = s?.loss_year;
        if (!x) break;
        const up = of100(base.loss_maker_turnaround.pct ?? 0);
        const e = profile.earnings;
        const prev = e[Y.prev];
        const trend = prev !== null && prev < 0 ? (Math.abs(x.net_income) < Math.abs(prev) ? `, menyusut dari rugi ${rpAmount(prev)} (${x.year - 1})` : `, lebih besar dari rugi ${rpAmount(prev)} (${x.year - 1})`) : "";
        const shrinking = prev !== null && prev < 0 && Math.abs(x.net_income) < Math.abs(prev);
        items.push({
          kind,
          title: "Perusahaan rugi",
          here: `Rugi bersih ${rpAmount(x.net_income)} pada ${x.year}${trend}.`,
          others: { figure: `${up} dari 100`, rest: "perusahaan rugi kembali untung pada tahun berikutnya." },
          meaning:
            prev !== null && prev < 0
              ? shrinking
                ? `kembali untung tahun depan terjadi pada ${quantifier(up)} perusahaan rugi, meski rugi ${code} sudah menyusut.`
                : `rugi ${code} justru membesar, dan kembali untung tahun depan terjadi pada ${quantifier(up)} perusahaan rugi.`
              : `kembali untung tahun depan terjadi pada ${quantifier(up)} perusahaan rugi.`,
        });
        break;
      }
      case "earnings_two_year_decline": {
        const x = s?.earnings_two_year_decline;
        if (!x) break;
        const up = of100(base.earnings_two_year_decline.pooled.rate * 100);
        items.push({
          kind,
          title: "Laba turun dua tahun",
          here: `Laba ${x.year - 2} ${rpAmount(x.earnings[0])}, ${x.year - 1} ${rpAmount(x.earnings[1])}, ${x.year} ${rpAmount(x.earnings[2])}.`,
          others: { figure: `${up} dari 100`, rest: "perusahaan yang labanya turun dua tahun, labanya naik lagi tahun berikutnya." },
          meaning: `laba naik lagi tahun depan terjadi pada ${quantifier(up)} kasus serupa, dan naik lagi belum berarti kembali ke laba semula.`,
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
          here: `Melantai ${dateLong(x.listing_date)} di Papan ${board}.`,
          others: tested ? { figure: `${Math.round(cell.negative_rate_pct)} dari 100`, rest: `IPO di Papan ${board} harganya di bawah penutupan hari pertama setahun kemudian.` } : null,
          meaning: `riwayat ${code} masih pendek, jadi sebagian perbandingan di halaman ini belum bisa dihitung.${tested ? "" : ` Papan ${board} tidak masuk uji IPO kami.`}`,
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
          here: `Laba ${x.year - 1} ${rpAmount(x.earnings[0])} ke ${x.year} ${rpAmount(x.earnings[1])}.`,
          others: { figure: `${lowerNext} dari 100`, rest: "perusahaan yang labanya melonjak seperti ini, labanya lebih rendah tahun berikutnya." },
          meaning: `laba ${code} turun lagi tahun depan terjadi pada ${quantifier(lowerNext)} kasus serupa.`,
        });
        break;
      }
      case "payout_above_earnings": {
        if (!flag(kind)) break;
        const pr = base.payout_above_100_cut_rate;
        items.push({
          kind,
          title: "Dividen melebihi laba",
          here: (() => {
            const pr = payoutOf(r);
            return pr !== null && pr > 1 ? `Membagikan ${idNum(pr * 100, 0)}% dari labanya sebagai dividen.` : "Dividen yang dibayar lebih besar dari labanya.";
          })(),
          others: { figure: outOfTen(pr.explore.cut_rate, pr.holdout.cut_rate), rest: "perusahaan yang membagikan lebih dari labanya memangkas dividen tahun berikutnya." },
          meaning: `dividen ${code} tahun depan belum tentu sebesar tahun ini.`,
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
          here: yNow !== undefined && yAvg !== undefined ? `${pctPlain(yNow)} sekarang, rata-rata ${code} sendiri ${pctPlain(yAvg)}.` : "Imbal dividen jauh di atas rata-rata perusahaan ini sendiri.",
          others: cut.rate === null ? null : { figure: `${of100(cut.rate * 100)} dari 100`, rest: `perusahaan dengan tanda ini memangkas dividen tahun berikutnya (${cut.n} kasus, ${cut.year}).` },
          meaning:
            cut.rate === null
              ? `imbal setinggi ini di ${code} biasanya karena harganya turun, bukan karena dividennya naik.`
              : `imbal ${code} yang tinggi belum tentu bertahan; ${quantifier(cut.rate * 100)} kasus serupa diikuti dividen yang dipangkas.`,
        });
        break;
      }
      case "near_ath_earnings_decline": {
        if (!flag(kind)) break;
        const neg = of100(base.near_peak_earnings_decline.pooled.share_negative * 100);
        items.push({
          kind,
          title: "Dekat puncak, laba turun",
          here: `Harga dalam 10% dari tertinggi sepanjang masa${profile.all_time_high !== null ? ` (${formatPrice(profile.all_time_high)})` : ""}, laba ${r.meta.years[Y.last]} lebih rendah dari ${r.meta.years[Y.prev]}.`,
          others: { figure: `${neg} dari 100`, rest: "saham dalam keadaan ini harganya lebih rendah 4 bulan kemudian." },
          meaning: `harga ${code} yang dekat puncak saat labanya turun diikuti harga lebih rendah pada ${quantifier(neg)} kasus serupa.`,
        });
        break;
      }
    }
  }
  return items.map((i) => ({ ...i, href: WATCH_HREF[i.kind] }));
}

/* ------------------------------------------------------------------ purpose answers */

export type { Answer, Evidence, Purpose };

function watchEvidence(items: WatchItem[], kinds: WatchKind[], code: string): Evidence[] {
  return items
    .filter((w) => kinds.includes(w.kind) && w.others)
    .map((w) => ({ text: `${code}: ${w.here} Pada saham lain, ${w.others!.figure} ${w.others!.rest}`, kind: "base" as const, href: w.href }));
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
  const yoy = last !== null && prev !== null && prev > 0 ? last / prev - 1 : null;
  const labaLine = yoy === null ? (last !== null && last < 0 ? `${code} rugi ${rpAmount(last)} pada ${years[Y.last]}.` : "") : `Laba ${code} ${years[Y.last]} ${yoy >= 0 ? "naik" : "turun"} ${pctPlain(yoy, 0)}.`;
  const rank = p.sector_rank_1y;
  const vsLine = chg === null ? "" : `Dalam setahun ${code} ${pctSigned(chg)}, IHSG ${pctSigned(meta.ihsg_change_1y)}.${rank && rank.n > 1 ? ` ${rank.better} dari ${rank.n} ${sectorStocks(r)} bergerak lebih baik.` : ""}`;
  const dist = price !== null && high ? pctFrom(price, high) : null;
  const spe = data.sector_context?.sector_typical_pe ?? null;
  const pressured = r.market.state === "tertekan";

  /* turun */
  const turunLead =
    dist === null
      ? `Harga ${code} tidak lengkap, jadi jaraknya dari harga tertinggi setahun tidak bisa dihitung.`
      : dist > -10
        ? `${code} tidak sedang turun jauh: ${signedPct(dist)} dari harga tertinggi setahunnya (${formatPrice(high)}).`
        : `${code} ${signedPct(dist)} dari harga tertinggi setahunnya (${formatPrice(high)}${p.w52_high_date ? `, ${dateLong(p.w52_high_date)}` : ""}).`;
  const turunEvidence = [
    ...watchEvidence(watch, ["fall", "long_below_peak"], code),
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
      lead: `P/E ${code} ${idNum(pe)}x${vsSector ? `: ${vsSector} nilai tengah sektornya (${idNum(spe!)}x)` : ""}, lebih rendah dari ${of100(p.pe_cheaper_than ?? 0)} dari 100 saham berlaba.`,
      body: `Artinya harga ${code} Rp ${idNum(pe)} untuk tiap Rp 1 laba setahun.${history}`,
      evidence: [
        inCheapThird
          ? tested(r, "low_pe", `P/E rendah ${code} masuk pola yang terbukti memberi hasil sedikit lebih baik, rata-rata ratusan saham. Pengaruhnya kecil.`)
          : notApplicable(r, "low_pe", `P/E ${code} tidak termasuk sepertiga termurah, jadi pola "P/E rendah" yang terbukti itu tidak berlaku di sini.`),
        ...(p.roe_ttm !== null ? [tested(r, "high_roe", `ROE ${code} ${pctPlain(p.roe_ttm)}. ROE tinggi tidak terbukti memprediksi hasil lebih baik.`)] : []),
        ...(p.pb_mrq !== null && p.pb_mrq > 0 ? [{ text: `P/B ${code} ${idNum(p.pb_mrq, 2)}x: harga pasarnya ${p.pb_mrq < 1 ? "di bawah" : "di atas"} nilai buku modal perusahaan.`, kind: null }] : []),
      ],
      check: [`P/E rendah bisa berarti pasar memperkirakan laba ${code} turun. Bandingkan dengan laporan laba kuartal berikutnya.`, `Bandingkan ${code} dengan ${sectorStocks(r)} lain, bukan dengan seluruh pasar.`],
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
      skipped_latest: `Tidak ada dividen untuk ${years[Y.last]}.`,
    };
    const payoutFlag = watch.find((w) => w.kind === "payout_above_earnings");
    dividen = {
      lead:
        dLast !== null && dLast > 0
          ? `${code} membagikan Rp ${idNum(dLast, dLast < 10 ? 2 : 0)} per saham untuk ${years[Y.last]}.${yieldNow !== null && yieldNow > 0 ? ` Imbal 12 bulan terakhir ${pctPlain(yieldNow)} dari harga sekarang.` : ""}`
          : `${code} tidak membagikan dividen untuk ${years[Y.last]}.`,
      body: `${yieldNow !== null && yieldNow > 0 ? `Lebih tinggi dari ${of100(p.yield_higher_than)} dari 100 saham. ` : ""}${history[dShape]}${payout !== null && payout > 0 ? ` ${code} membagikan ${idNum(payout * 100, 0)}% dari labanya.` : ""}`,
      evidence: [
        isHighYield(p)
          ? tested(r, "high_yield", `Dividen ${code} termasuk sepertiga tertinggi di antara pembayar dividen. Saham berdividen tinggi terbukti memberi hasil sedikit lebih baik, rata-rata.`)
          : notApplicable(r, "high_yield", `Dividen ${code} tidak termasuk sepertiga tertinggi di antara pembayar dividen, jadi pola "dividen tinggi" yang terbukti itu tidak berlaku di sini.`),
        ...(payoutFlag
          ? watchEvidence(watch, ["payout_above_earnings"], code)
          : payout !== null && payout > 0 && payout <= 1
            ? [{ text: `${code} membagikan ${idNum(payout * 100, 0)}% dari labanya, di bawah 100%. Perusahaan yang membagikan lebih dari labanya memangkas dividen ${outOfTen(r.base.payout_above_100_cut_rate.explore.cut_rate, r.base.payout_above_100_cut_rate.holdout.cut_rate)} kali; ${code} tidak dalam keadaan itu.`, kind: "base" as const }]
            : []),
        ...watchEvidence(watch, ["yield_far_above_average"], code),
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
      ? `${code} naik ${pctPlain(chg)} dalam setahun, saat IHSG ${pctSigned(meta.ihsg_change_1y)}.`
      : chg === null && price !== null && low
        ? `${code} ${signedPct(pctFrom(price, low), 1, true)} dari harga terendah setahunnya (${formatPrice(low)}${p.w52_low_date ? `, ${dateLong(p.w52_low_date)}` : ""})${dist !== null ? ` dan ${signedPct(dist)} dari tertingginya` : ""}.`
        : `${code} tidak sedang naik tinggi: ${chg !== null ? `${pctSigned(chg)} setahun` : "perubahan setahun tidak tersedia"}${dist !== null ? `, ${signedPct(dist)} dari tertinggi setahun` : ""}.`;
  const peLine = p.pe_meaningful && p.pe_ttm !== null ? ` Harga ${code} sekarang ${idNum(p.pe_ttm, 0)} kali laba setahun${isMeaningfulPe(spe) ? `, nilai tengah sektornya ${idNum(spe, 0)} kali` : ""}.` : "";
  const naik: Answer = {
    lead: naikLead,
    body: `${labaLine}${peLine}`.trim() || vsLine,
    evidence: [
      ...watchEvidence(watch, ["recent_spike", "recent_price_suspension", "repeat_suspension"], code),
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
      body: [vsLine, pressured ? `IHSG sendiri sedang tertekan: ${pctPlain(r.market.pct_from_peak)} di bawah puncaknya.` : "", labaLine].filter(Boolean).join(" "),
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
  const share = payout !== null && payout > 0 && shape !== "never" ? ` Perusahaan membagikan ${idNum(payout * 100, 0)}% dari labanya.` : "";
  return `${how}${share}`;
}

/** "Perusahaan terbesar ke-11 dari 962 di bursa, nilai pasar Rp 198,8 T." */
export function sizeLine(r: ReadInput): string | null {
  const { market_cap, market_cap_rank } = r.data.snapshot;
  if (market_cap === null || market_cap_rank === null) return null;
  return `Perusahaan terbesar ke-${market_cap_rank} dari ${r.universe} di bursa, nilai pasar ${rpAmount(market_cap)}.`;
}
