import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { BaseRatesData } from "@/lib/base-rates-data";
import type { IpoBoardsData } from "@/lib/ipo-boards-data";
import type { StockPageData } from "@/lib/stock-data";
import type { StockSituationEntry } from "@/lib/stock-situations";
import { buildKeyRows, buildStockCard, situationLinesFor } from "./stock-card";

const dataDir = path.join(__dirname, "..", "..", "..", "..", "data", "app");
const read = <T>(file: string) => JSON.parse(readFileSync(path.join(dataDir, file), "utf-8")) as T;
const stocks = read<{ stocks: Record<string, StockPageData> }>("stocks.json").stocks;
const base = read<BaseRatesData>("base_rates.json");
const ipo = read<IpoBoardsData>("ipo_boards.json");
const recovered = read<{ long_below_peak: { recovered_by_504: { rate: number } } }>("base_rates.json").long_below_peak.recovered_by_504.rate;

const none: StockSituationEntry = { fall: null, older_fall: null, loss_year: null, recent_price_suspension: null, recent_ipo: null, recent_spike: null, earnings_two_year_decline: null, earnings_more_than_doubled: null, long_below_peak: null, repeat_suspension: null };

describe("buildStockCard", () => {
  const bbca = stocks["BBCA.JK"];

  it("formats the head line from the snapshot, the change being the distance from the 52-week high", () => {
    const card = buildStockCard("BBCA", bbca, 962);
    expect(card.name).toBe("Bank Central Asia");
    expect(card.price).toMatch(/^Rp [\d.]+$/);
    expect(card.change).toMatch(/^-?[\d,]+%$/);
    expect(card.negative).toBe(card.change?.startsWith("-"));
  });

  it("lists market value, ROE and P/E with their sector comparison", () => {
    const rows = buildKeyRows(bbca, 962);
    expect(rows.map((r) => r.label)).toEqual(["Nilai pasar", "ROE", "P/E"]);
    expect(rows[0].value).toMatch(/^Rp [\d.,]+ triliun, terbesar ke-\d+ dari 962 saham$/);
    expect(rows[1].value).toMatch(/nilai tengah sektor/);
  });

  it("leaves out a row it has no data for", () => {
    const bare = { ...bbca, snapshot: { ...bbca.snapshot, market_cap: null }, sector_context: null };
    expect(buildKeyRows(bare, 962)).toEqual([]);
  });
});

describe("situationLinesFor", () => {
  const inputs = { base, ipo, longBelowRecovered: recovered };

  it("gives nothing for a stock in no situation", () => {
    expect(situationLinesFor(undefined, inputs)).toEqual([]);
    expect(situationLinesFor(none, inputs)).toEqual([]);
  });

  it("words an old fall as a natural frequency from the long-below-peak base rate", () => {
    const older = { peak_price: 1, peak_date: "2022-01-01", trigger_date: "2022-02-01", trigger_price: 1, trading_days_since: 1, window_trading_days: 1, last_close: 1, last_close_date: "2026-09-13", pct_from_peak: -30 };
    const [line] = situationLinesFor({ ...none, older_fall: older }, inputs);
    expect(line.title).toBe("Jauh di bawah puncak lama");
    expect(line.line).toBe(`Dari 100 saham seperti ini, ${Math.round(recovered * 100)} kembali ke puncak setahun kemudian.`);
  });

  it("keeps each situation on its own line, none combined", () => {
    const loss = { year: 2025, net_income: -1 };
    const doubled = { year: 2025, earnings: [1, 3] };
    const lines = situationLinesFor({ ...none, loss_year: loss, earnings_more_than_doubled: doubled }, inputs);
    expect(lines.map((l) => l.kind)).toEqual(["loss_year", "earnings_more_than_doubled"]);
    for (const l of lines) expect(l.line).toMatch(/^Dari 100 /);
  });
});
