import { readFile } from "node:fs/promises";
import path from "node:path";
import { getExtraBaseRates, yieldCutRate } from "@/lib/anomaly-data";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { getFindingsData } from "@/lib/findings-data";
import { getInsiderSummary } from "@/lib/insider-data";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { getMarketConditionData } from "@/lib/market-condition-data";
import { getNewsSentiment } from "@/lib/news-data";
import { sectorByKey } from "@/lib/sectors-id";
import { getAllStockCodes, getStockData, type StockPageData } from "@/lib/stock-data";
import { getGainRankCount, getProfileMeta, getStockProfile } from "@/lib/stock-profile-data";
import { findingRefs, type ReadInput } from "@/lib/stock-read";
import { getSituationsFile } from "@/lib/stock-situations";

/** Everything the stock-page rules (lib/stock-read.ts) read, for one stock. Server-only. */
export async function getReadInput(code: string, data: StockPageData): Promise<ReadInput | null> {
  const [profile, meta, situations, base, ipo, extra, findings, news, market, gainRankCount, codes, insider] = await Promise.all([
    getStockProfile(code),
    getProfileMeta(),
    getSituationsFile(),
    getBaseRatesData(),
    getIpoBoardsData(),
    getExtraBaseRates(),
    getFindingsData(),
    getNewsSentiment(),
    getMarketConditionData(),
    getGainRankCount(),
    getAllStockCodes(),
    getInsiderSummary(),
  ]);
  if (!profile) return null;
  return {
    code,
    sector: sectorByKey(data.snapshot.sector)?.label ?? null,
    data,
    profile,
    meta,
    situations: situations.by_symbol[`${code}.JK`],
    base,
    ipo,
    yieldCut: yieldCutRate(extra),
    findings: findingRefs(findings.scoreboard),
    news: news.by_symbol[code] ?? null,
    newsMarket: { bullishPct: news.bullish_mentions_pct, first: news.first_date, last: news.last_date },
    market: { state: market.ihsg.state, pct_from_peak: market.ihsg.pct_from_peak },
    gainRankCount,
    universe: codes.length,
    insiderSince: insider.window.start,
  };
}

export interface PeerBank {
  code: string;
  pe: number | null;
  yield: number | null;
  change1y: number | null;
}

/** The three largest other banks (by market value) for the bank card's "Bank besar lain". */
export async function getPeerBanks(code: string): Promise<PeerBank[]> {
  const raw = JSON.parse(await readFile(path.join(process.cwd(), "..", "data", "app", "lens_banking.json"), "utf-8")) as { banks: Record<string, unknown> };
  const rows = await Promise.all(
    Object.keys(raw.banks)
      .map((s) => s.replace(/\.JK$/, ""))
      .filter((c) => c !== code)
      .map(async (c) => ({ c, data: await getStockData(c), p: await getStockProfile(c) }))
  );
  return rows
    .filter((r) => r.data?.snapshot.market_cap != null && r.p)
    .sort((a, b) => (b.data!.snapshot.market_cap ?? 0) - (a.data!.snapshot.market_cap ?? 0))
    .slice(0, 3)
    .map(({ c, p }) => ({ code: c, pe: p!.pe_meaningful ? p!.pe_ttm : null, yield: p!.yield_ttm, change1y: p!.change_1y }));
}
