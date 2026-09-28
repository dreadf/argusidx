import { readFile } from "node:fs/promises";
import path from "node:path";
import { getBaseRatesData, type BaseRatesData } from "@/lib/base-rates-data";
import { getFlagsData, type FlagsData } from "@/lib/flags-data";
import { getSituations, H11_UNDERPERFORM } from "@/lib/situations";
import { STRESS } from "@/lib/evidence-constants";

/**
 * Temuan > Tanda list rows (formerly "Deteksi anomali"). Every count and rate comes from
 * data/app/situations.json (counts), base_rates.json and flags.json; the
 * one exception is the H11 suspension result, which only exists as the
 * pinned constant in lib/situations.ts. Server-only (fs).
 */

export type AnomalyGroup = "Harga" | "Laporan keuangan" | "Dividen";
export type AnomalyIcon = "spike" | "pause" | "double" | "decline" | "flag";
export type FlagKind = "payout" | "puncak-laba" | "dividen-tinggi";

export interface AnomalyRow {
  key: string;
  group: AnomalyGroup;
  icon: AnomalyIcon;
  title: string;
  isNew: boolean;
  /** "N saham. base-rate sentence" */
  line: string;
  /** Situation slug when the row has a situation page. */
  situationSlug: string | null;
  /** Flag detail page, used when there is no situation page. */
  flagKind: FlagKind | null;
}

/** The base_rates.json blocks not typed in base-rates-data.ts. */
export interface ExtraBaseRates {
  repeat_spike_suspension: { share_followed: number };
  near_peak_earnings_decline: { pooled: { share_negative: number } };
  yield_spike_cut: Record<string, { triggered: number; cut_missing_counted_as_cut: { rate: number | null; n?: number } }>;
  payout_above_100_cut_rate: { explore: { cut_rate: number }; holdout: { cut_rate: number } };
}

export interface SituationCounts {
  recent_spike: number;
  recent_price_suspension: number;
  repeat_suspension: number;
  earnings_more_than_doubled: number;
  earnings_two_year_decline: number;
}

/** Whole "out of 100" for a 0..1 rate. */
const of100 = (rate: number) => Math.round(rate * 100);

/** "6 sampai 8 dari 10" from two rates, or "7 dari 10" when they round the same. */
export function outOfTen(a: number, b: number): string {
  const lo = Math.round(Math.min(a, b) * 10);
  const hi = Math.round(Math.max(a, b) * 10);
  return lo === hi ? `${lo} dari 10` : `${lo} sampai ${hi} dari 10`;
}

export function buildAnomalyRows(counts: SituationCounts, base: BaseRatesData, extra: ExtraBaseRates, flags: FlagsData): AnomalyRow[] {
  // Count: stocks flagged now (the same definition the flag page lists). Rate: the newest past year whose next-year cut is already known, with its case count.
  const years = Object.keys(extra.yield_spike_cut).sort();
  const withRate = years.map((y) => extra.yield_spike_cut[y]).reverse().find((y) => y.cut_missing_counted_as_cut.rate !== null);
  const cutRate = withRate?.cut_missing_counted_as_cut.rate ?? null;
  const cutCases = withRate?.cut_missing_counted_as_cut.n ?? null;
  const cutYear = years.find((y) => extra.yield_spike_cut[y] === withRate) ?? "";

  return [
    {
      key: "harga-baru-melonjak",
      group: "Harga",
      icon: "spike",
      title: "Harga baru melonjak",
      isNew: false,
      line: `${counts.recent_spike} saham. ${of100(base.recent_spike.pooled.share_below_event_close)} dari 100 lebih rendah 60 hari kemudian`,
      situationSlug: "harga-baru-melonjak",
      flagKind: null,
    },
    {
      key: "suspensi-lonjakan",
      group: "Harga",
      icon: "pause",
      title: "Suspensi karena lonjakan",
      isNew: false,
      line: `${counts.recent_price_suspension} saham. ${H11_UNDERPERFORM.holdout} dari 100 kalah dari indeks dalam 90 hari`,
      situationSlug: "pernah-disuspensi",
      flagKind: null,
    },
    {
      key: "langganan-suspensi",
      group: "Harga",
      icon: "pause",
      title: "Langganan suspensi",
      isNew: true,
      line: `${counts.repeat_suspension} saham. ${of100(extra.repeat_spike_suspension.share_followed)} dari 100 disuspensi lagi dalam setahun`,
      situationSlug: "langganan-suspensi",
      flagKind: null,
    },
    {
      key: "laba-dua-kali-lipat",
      group: "Laporan keuangan",
      icon: "double",
      title: "Laba lebih dari dua kali lipat",
      isNew: false,
      line: `${counts.earnings_more_than_doubled} perusahaan. ${of100(base.earnings_more_than_doubled.gave_part_back.rate)} dari 100 labanya turun lagi`,
      situationSlug: "laba-dua-kali-lipat",
      flagKind: null,
    },
    {
      key: "laba-turun-dua-tahun",
      group: "Laporan keuangan",
      icon: "decline",
      title: "Laba turun dua tahun",
      isNew: false,
      line: `${counts.earnings_two_year_decline} perusahaan. ${of100(base.earnings_two_year_decline.pooled.rate)} dari 100 labanya naik lagi`,
      situationSlug: "laba-turun-dua-tahun",
      flagKind: null,
    },
    {
      key: "dekat-puncak-laba-turun",
      group: "Laporan keuangan",
      icon: "flag",
      title: "Dekat puncak, laba menurun",
      isNew: false,
      line: `${flags.near_ath_earnings_decline.flagged_count} saham. ${of100(extra.near_peak_earnings_decline.pooled.share_negative)} dari 100 rugi dalam 4 bulan`,
      situationSlug: "dekat-puncak-laba-turun",
      flagKind: "puncak-laba",
    },
    {
      key: "dividen-melebihi-laba",
      group: "Dividen",
      icon: "flag",
      title: "Dividen melebihi laba",
      isNew: true,
      line: `${flags.payout_above_earnings.flagged_count} perusahaan. ${outOfTen(extra.payout_above_100_cut_rate.explore.cut_rate, extra.payout_above_100_cut_rate.holdout.cut_rate)} memangkas dividen tahun berikutnya`,
      situationSlug: "dividen-besar",
      flagKind: "payout",
    },
    {
      key: "dividen-di-atas-rata-rata",
      group: "Dividen",
      icon: "flag",
      title: "Dividen jauh di atas rata-rata sendiri",
      isNew: true,
      line: `${flags.yield_far_above_average.flagged_count} perusahaan. ${cutRate === null ? "Belum ada hasil tahun berikutnya" : `${of100(cutRate)} dari 100 memangkas dividen tahun berikutnya${cutCases ? ` (${cutCases} kasus, ${cutYear}, satu tahun saja); semua pembayar dividen: ${Math.round(STRESS.ordinary.i9CutAllPayers)}` : ""}`}`,
      situationSlug: null,
      flagKind: "dividen-tinggi",
    },
  ];
}

export async function getAnomalyRows(): Promise<{ rows: AnomalyRow[]; asOf: string; situationSlugs: Set<string> }> {
  const dir = path.join(process.cwd(), "..", "data", "app");
  const [base, flags, sit, extra] = await Promise.all([
    getBaseRatesData(),
    getFlagsData(),
    readFile(path.join(dir, "situations.json"), "utf-8").then((s) => JSON.parse(s) as { as_of: string; counts: SituationCounts }),
    readFile(path.join(dir, "base_rates.json"), "utf-8").then((s) => JSON.parse(s) as ExtraBaseRates),
  ]);
  const situationSlugs = new Set((await getSituations()).map((s) => s.slug));
  return { rows: buildAnomalyRows(sit.counts, base, extra, flags), asOf: sit.as_of, situationSlugs };
}
