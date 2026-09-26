import { readFile } from "node:fs/promises";
import path from "node:path";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { findingSlug, getFindingsData } from "@/lib/findings-data";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { getSituations } from "@/lib/situations";
import { getAllStockCodes, getStockData } from "@/lib/stock-data";
import { getSituationsFile } from "@/lib/stock-situations";
import { buildStockCard, situationLinesFor } from "./stock-card";
import type { SituationId } from "./tip-claims";
import type { TipBundle, TipBundleStock } from "./tip-view";

/** base_rates.json key with no typed loader: share of long-below-peak stocks back at the old peak by day 504. */
async function longBelowRecovered(): Promise<number | null> {
  const raw = await readFile(path.join(process.cwd(), "..", "data", "app", "base_rates.json"), "utf-8");
  const rate = (JSON.parse(raw) as { long_below_peak?: { recovered_by_504?: { rate?: number } } }).long_below_peak?.recovered_by_504?.rate;
  return typeof rate === "number" ? rate : null;
}

const SITUATION_SLUG: Record<SituationId, string> = { spike: "harga-baru-melonjak", fall: "turun-banyak", ipo: "ikut-ipo", suspension: "pernah-disuspensi" };

let cached: TipBundle | null = null;

/**
 * Everything the browser needs to read a pasted message on its own: the stock
 * list, the tested findings and the situation lines, all from data/app. Built
 * once per server process. Contains nothing about any user's message.
 */
export async function getTipBundle(): Promise<TipBundle> {
  if (cached) return cached;
  const [codes, findings, situations, sitFile, base, ipo, recovered] = await Promise.all([
    getAllStockCodes(),
    getFindingsData(),
    getSituations(),
    getSituationsFile(),
    getBaseRatesData(),
    getIpoBoardsData(),
    longBelowRecovered(),
  ]);

  const ranked: { stock: TipBundleStock; rank: number }[] = [];
  for (const code of codes) {
    const data = await getStockData(code);
    if (!data) continue;
    const card = buildStockCard(code, data, codes.length);
    ranked.push({
      rank: data.snapshot.market_cap_rank ?? Number.MAX_SAFE_INTEGER,
      stock: {
        code,
        name: data.snapshot.company_name,
        short: card.name,
        price: card.price,
        change: card.change,
        negative: card.negative,
        situations: situationLinesFor(sitFile.by_symbol[`${code}.JK`], { base, ipo, longBelowRecovered: recovered }),
      },
    });
  }
  ranked.sort((a, b) => a.rank - b.rank);

  const situationClaims: TipBundle["situationClaims"] = {};
  for (const id of Object.keys(SITUATION_SLUG) as SituationId[]) {
    const meta = situations.find((s) => s.slug === SITUATION_SLUG[id]);
    if (meta) situationClaims[id] = { slug: meta.slug, line: meta.line };
  }

  cached = {
    stocks: ranked.map((r) => r.stock),
    findings: findings.scoreboard.map((f) => ({
      belief: f.belief,
      hypothesisId: f.evidence.hypothesis_id,
      slug: findingSlug(f),
      verdict: f.verdict,
      title: f.title_short_id,
      line: f.result_short_id,
    })),
    situationClaims,
  };
  return cached;
}
