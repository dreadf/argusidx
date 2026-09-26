import type { BaseRatesData } from "@/lib/base-rates-data";
import { formatPrice, idNum, pctFrom, shortName, signedPct } from "@/lib/format";
import type { IpoBoardsData } from "@/lib/ipo-boards-data";
import { formatPe, isMeaningfulPe } from "@/lib/pe";
import { H11_UNDERPERFORM } from "@/lib/situations";
import type { StockPageData } from "@/lib/stock-data";
import type { StockSituationEntry } from "@/lib/stock-situations";

/**
 * Compact stock summary shown in Tanya results (boards Tanya-Tempel-Hasil and
 * Tanya-AI-Habis): the head line, the key facts, and the situation lines a
 * stock is in. Pure: strings are formatted here so the browser only renders.
 * Server code builds these from data/app; the browser imports only the types.
 */
export interface StockCardRow {
  label: string;
  value: string;
}

export interface SituationLine {
  kind: "fall" | "older_fall" | "recent_spike" | "recent_price_suspension" | "loss_year" | "earnings_two_year_decline" | "earnings_more_than_doubled" | "recent_ipo";
  title: string;
  /** One line, natural frequency. */
  line: string;
  href: string;
}

export interface StockCard {
  code: string;
  name: string;
  /** "Rp 6.325", or null when there is no last close. */
  price: string | null;
  /** Distance from the 52-week high, signed ("-27,7%"), or null. */
  change: string | null;
  negative: boolean;
  rows: StockCardRow[];
}

/** Nilai pasar / ROE / P/E, each with its comparison. Rows with no data are left out. */
export function buildKeyRows(data: StockPageData, universe: number): StockCardRow[] {
  const { snapshot: s, sector_context: sc } = data;
  const rows: StockCardRow[] = [];
  if (s.market_cap !== null) {
    rows.push({ label: "Nilai pasar", value: `Rp ${idNum(s.market_cap / 1e12, 1)} triliun${s.market_cap_rank !== null ? `, terbesar ke-${s.market_cap_rank} dari ${universe} saham` : ""}` });
  }
  if (sc && sc.own_roe_pct !== null) {
    rows.push({ label: "ROE", value: `${idNum(sc.own_roe_pct)}%${sc.sector_typical_roe_pct !== null ? `, nilai tengah sektor ${sc.sector} ${idNum(sc.sector_typical_roe_pct)}%` : ""}` });
  }
  if (sc && sc.own_pe !== null) {
    rows.push({ label: "P/E", value: isMeaningfulPe(sc.own_pe) && isMeaningfulPe(sc.sector_typical_pe) ? `${formatPe(sc.own_pe)}, nilai tengah sektor ${formatPe(sc.sector_typical_pe)}` : formatPe(sc.own_pe) });
  }
  return rows;
}

export function buildStockCard(code: string, data: StockPageData, universe: number): StockCard {
  const { snapshot: s } = data;
  const price = s.last_close_price;
  const high = s["52_w_high_price"];
  const change = price !== null && high ? pctFrom(price, high) : null;
  return {
    code,
    name: shortName(s.company_name),
    price: price === null ? null : formatPrice(price),
    change: change === null ? null : signedPct(change),
    negative: change !== null && change < 0,
    rows: buildKeyRows(data, universe),
  };
}

export interface SituationInputs {
  base: BaseRatesData;
  ipo: IpoBoardsData;
  /** Share (0..1) of long-below-peak stocks that got back to the old peak by day 504, from base_rates.json. */
  longBelowRecovered: number | null;
}

const BOARD_ID: Record<string, string> = { Acceleration: "Akselerasi", Main: "Utama" };

/**
 * One title and one natural-frequency line per situation the stock is in now
 * (situations.json), from the same base rates the stock page uses. Each stands
 * alone, nothing is combined. A situation we hold no frequency for gets no line.
 */
export function situationLinesFor(entry: StockSituationEntry | undefined, inputs: SituationInputs): SituationLine[] {
  if (!entry) return [];
  const { base, ipo, longBelowRecovered } = inputs;
  const out: SituationLine[] = [];

  if (entry.fall) {
    const below = Math.round(base.recovery_after_fall.still_below_peak.pct ?? 0);
    out.push({ kind: "fall", title: "Jatuh jauh dari puncak", line: `Dari 100 saham yang jatuh 30%, ${below} belum kembali ke puncaknya setahun kemudian.`, href: "/situasi/turun-banyak" });
  } else if (entry.older_fall && longBelowRecovered !== null) {
    out.push({ kind: "older_fall", title: "Jauh di bawah puncak lama", line: `Dari 100 saham seperti ini, ${Math.round(longBelowRecovered * 100)} kembali ke puncak setahun kemudian.`, href: "/situasi/turun-banyak" });
  }
  if (entry.recent_spike) {
    const below = Math.round(base.recent_spike.pooled.share_below_event_close * 100);
    out.push({ kind: "recent_spike", title: "Harga baru melonjak", line: `Dari 100 saham yang naik 40% atau lebih dalam 20 hari bursa, ${below} berakhir lebih rendah 60 hari bursa kemudian.`, href: "/situasi/harga-baru-melonjak" });
  }
  if (entry.recent_price_suspension) {
    out.push({ kind: "recent_price_suspension", title: "Suspensi karena lonjakan", line: `Dari 100 saham yang disuspensi karena lonjakan harga, ${H11_UNDERPERFORM.holdout} kalah dari indeks dalam 90 hari sesudahnya.`, href: "/situasi/pernah-disuspensi" });
  }
  if (entry.loss_year) {
    out.push({ kind: "loss_year", title: "Perusahaan rugi setahun", line: `Dari 100 perusahaan yang rugi setahun, ${Math.round(base.loss_maker_turnaround.pct ?? 0)} untung lagi di tahun berikutnya.`, href: "/situasi/perusahaan-rugi" });
  }
  if (entry.earnings_two_year_decline) {
    out.push({ kind: "earnings_two_year_decline", title: "Laba turun dua tahun", line: `Dari 100 perusahaan yang labanya turun dua tahun, ${Math.round(base.earnings_two_year_decline.pooled.rate * 100)} labanya naik lagi tahun berikutnya.`, href: "/situasi/laba-turun-dua-tahun" });
  }
  if (entry.earnings_more_than_doubled) {
    out.push({ kind: "earnings_more_than_doubled", title: "Laba lebih dari dua kali lipat", line: `Dari 100 perusahaan yang labanya lebih dari dua kali lipat, ${Math.round(base.earnings_more_than_doubled.gave_part_back.rate * 100)} labanya lebih rendah tahun berikutnya.`, href: "/situasi/laba-dua-kali-lipat" });
  }
  if (entry.recent_ipo) {
    const board = entry.recent_ipo.board;
    const cell = ipo.holdout.horizons["365d"].by_board[board];
    if (cell && BOARD_ID[board]) {
      out.push({ kind: "recent_ipo", title: "IPO setahun terakhir", line: `Dari 100 IPO di Papan ${BOARD_ID[board]}, ${Math.round(cell.negative_rate_pct)} harganya di bawah penutupan hari pertama setahun kemudian.`, href: "/situasi/ikut-ipo" });
    }
  }
  return out;
}
