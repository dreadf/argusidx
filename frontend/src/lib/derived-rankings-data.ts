import { readFile } from "node:fs/promises";
import path from "node:path";
import type { RankRow } from "@/components/rank-list";
import { idNum, sharePct, shortName, signedPct, stripJk } from "@/lib/format";

/** The four derived rankings (data/app/rankings_derived.json). Server-only (fs). */

export interface RoeRow {
  symbol: string;
  company_name: string;
  roe_2025: number;
  percentile: number;
  group: string;
  group_level: string;
  group_size: number;
}
export interface DividendRow {
  symbol: string;
  company_name: string;
  years_paid: number;
  of_years: number;
  variation: number;
}
export interface StreakRow {
  symbol: string;
  company_name: string;
  rising_years: number;
}
export interface InsiderRow {
  symbol: string;
  company_name: string;
  net_shares: number;
  share_of_outstanding: number;
  n_filings: number;
}

export interface RankingsDerived {
  as_of: string;
  roe_vs_peers: { cara_menghitung: string; evaluable_count: number; excluded_over_100_percent: RoeRow[]; top: RoeRow[] };
  dividend_consistency: { cara_menghitung: string; evaluable_count: number; top: DividendRow[] };
  earnings_streaks: { cara_menghitung: string; evaluable_count: number; longest_run: number; stocks_at_longest_run: number; top: StreakRow[] };
  net_insider: {
    cara_menghitung: string;
    filings_used: number;
    filings_tagged_takeover: number;
    evaluable_count: number;
    excluded_over_100_percent: InsiderRow[];
    top_net_buyers: InsiderRow[];
  };
}

export type DerivedSlug = "roe-dalam-kelompok" | "dividen-rutin" | "laba-naik-berturut" | "orang-dalam-beli";

export const DERIVED_SLUGS: DerivedSlug[] = ["roe-dalam-kelompok", "dividen-rutin", "laba-naik-berturut", "orang-dalam-beli"];

export async function getRankingsDerived(): Promise<RankingsDerived> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "rankings_derived.json");
  const parsed = JSON.parse(await readFile(filePath, "utf-8")) as RankingsDerived;
  const strip = <T extends { symbol: string }>(rows: T[]): T[] => rows.map((r) => ({ ...r, symbol: stripJk(r.symbol) }));
  return {
    ...parsed,
    roe_vs_peers: { ...parsed.roe_vs_peers, excluded_over_100_percent: strip(parsed.roe_vs_peers.excluded_over_100_percent), top: strip(parsed.roe_vs_peers.top) },
    dividend_consistency: { ...parsed.dividend_consistency, top: strip(parsed.dividend_consistency.top) },
    earnings_streaks: { ...parsed.earnings_streaks, top: strip(parsed.earnings_streaks.top) },
    net_insider: {
      ...parsed.net_insider,
      excluded_over_100_percent: strip(parsed.net_insider.excluded_over_100_percent),
      top_net_buyers: strip(parsed.net_insider.top_net_buyers),
    },
  };
}

export interface DerivedView {
  title: string;
  line: string;
  rows: RankRow[];
  /** Honest statement of ties in the list, or null when there are none. */
  ties: string | null;
  /** cara_menghitung, verbatim from the data. */
  method: string;
  /** Rows left out of the list, disclosed in a short note; null when there is nothing to disclose. */
  excluded: string | null;
}

/** How many leading rows share the first row's key. */
export function tiedAtTop<T>(rows: T[], key: (r: T) => number | string): number {
  if (rows.length === 0) return 0;
  const first = key(rows[0]);
  return rows.filter((r) => key(r) === first).length;
}

const codes = (rows: { symbol: string }[]) => rows.map((r) => r.symbol).join(", ");

export function buildDerivedView(slug: DerivedSlug, d: RankingsDerived): DerivedView {
  switch (slug) {
    case "roe-dalam-kelompok": {
      const b = d.roe_vs_peers;
      const ex = b.excluded_over_100_percent;
      const tied = tiedAtTop(b.top, (r) => r.percentile);
      return {
        title: "ROE tertinggi dalam kelompoknya",
        line: `Persentil ROE 2025 di antara perusahaan sejenis. ${idNum(b.evaluable_count, 0)} saham dihitung.`,
        rows: b.top.map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: `ROE ${sharePct(r.roe_2025)}`, sub: `persentil ${idNum(r.percentile, 0)}` })),
        ties: tied > 1 ? `${tied} dari ${b.top.length} saham di daftar ini sama-sama di persentil ${idNum(b.top[0].percentile, 0)}. Urutan di antara mereka mengikuti aturan seri di bawah.` : null,
        method: b.cara_menghitung,
        excluded: ex.length ? `${ex.length} saham tidak ditampilkan karena ROE 2025 di atas 100%: ${codes(ex)}.` : null,
      };
    }
    case "dividen-rutin": {
      const b = d.dividend_consistency;
      const sameYears = tiedAtTop(b.top, (r) => r.years_paid);
      return {
        title: "Dividen paling rutin",
        line: `Tahun membayar dividen dari 2021 sampai 2025. ${idNum(b.evaluable_count, 0)} saham dihitung.`,
        rows: b.top.map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: `${r.years_paid} dari ${r.of_years}`, sub: `variasi ${idNum(r.variation, 2)}` })),
        ties: sameYears > 1 ? `${sameYears} dari ${b.top.length} saham di daftar ini sama-sama membayar ${b.top[0].years_paid} dari ${b.top[0].of_years} tahun. Urutan di antara mereka mengikuti aturan seri di bawah.` : null,
        method: b.cara_menghitung,
        excluded: null,
      };
    }
    case "laba-naik-berturut": {
      const b = d.earnings_streaks;
      return {
        title: "Laba naik berturut-turut",
        line: `Rentetan kenaikan laba tahunan sampai 2025. ${idNum(b.evaluable_count, 0)} saham dihitung.`,
        rows: b.top.map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: `${r.rising_years} tahun`, sub: "laba naik beruntun" })),
        ties: `${b.stocks_at_longest_run} saham sama-sama di rentetan terpanjang, ${b.longest_run} tahun. Daftar ini hanya menampilkan ${b.top.length} dari mereka, menurut kode saham.`,
        method: b.cara_menghitung,
        excluded: null,
      };
    }
    case "orang-dalam-beli": {
      const b = d.net_insider;
      const ex = b.excluded_over_100_percent;
      return {
        title: "Pembelian bersih orang dalam",
        line: `Selisih beli dan jual dibanding saham beredar. ${idNum(b.evaluable_count, 0)} saham dihitung.`,
        rows: b.top_net_buyers.map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: signedPct(r.share_of_outstanding * 100, 1, true), sub: `${r.n_filings} laporan` })),
        ties: null,
        method: b.cara_menghitung,
        excluded: `${ex.length ? `${ex.length} saham tidak ditampilkan karena selisihnya lebih dari 100% saham beredar: ${codes(ex)}. ` : ""}${b.filings_tagged_takeover} laporan bertanda takeover tidak dihitung di daftar ini.`,
      };
    }
  }
}
