import { describe, expect, it } from "vitest";
import type { StockPageData } from "@/lib/stock-data";
import type { WatchItem } from "@/lib/stock-read";
import { buildFingerprint, describeChanges, type StockFingerprint } from "@/lib/watchlist-changes";

function watchItem(kind: string, title: string): WatchItem {
  return { kind: kind as WatchItem["kind"], title, here: "", others: null, meaning: "", href: "" };
}

function stockData(overrides: Partial<StockPageData> = {}): StockPageData {
  return {
    snapshot: {} as StockPageData["snapshot"],
    peer_comparison: null,
    sector_context: null,
    flags: [],
    suspension_history: null,
    lens_banking: null,
    lens_extractive: null,
    beat_gold: null,
    h1_finding: null,
    insider_activity: null,
    corporate_actions: { as_of: "2026-09-20", window_start: "2026-08-21", window_end: "2026-10-20", dividends: [], agms: [], rights_issues: [], stock_splits: [] },
    ...overrides,
  };
}

describe("buildFingerprint", () => {
  it("sorts and de-duplicates active watch kinds", () => {
    const fp = buildFingerprint(stockData(), [watchItem("loss_year", "Perusahaan rugi"), watchItem("fall", "Turun banyak"), watchItem("fall", "Turun banyak")]);
    expect(fp.watch).toEqual(["fall", "loss_year"]);
  });

  it("takes the newest date of each corporate-action kind", () => {
    const data = stockData({
      corporate_actions: {
        as_of: "2026-09-20",
        window_start: "2026-08-21",
        window_end: "2026-10-20",
        dividends: [
          { ex_date: "2026-05-05", payment_date: null, amount: 100, implied_yield: null },
          { ex_date: "2026-09-01", payment_date: null, amount: 120, implied_yield: null },
        ],
        agms: [{ agm_date: "2026-09-10", agm_time: null, cancelled: false }],
        rights_issues: [],
        stock_splits: [],
      },
    });
    const fp = buildFingerprint(data, []);
    expect(fp.lastDividendExDate).toBe("2026-09-01");
    expect(fp.lastAgmDate).toBe("2026-09-10");
    expect(fp.lastRightsExDate).toBeNull();
  });

  it("reads the newest suspension date and the insider date, both optional", () => {
    const withBoth = stockData({
      suspension_history: { events: [{ date: "2026-01-10", reason: "", pdf_url: "", category: "", category_label_id: "", group: "", group_label_id: "" }], count: 1, universe_count: 900, companies_with_suspensions: 1, base_rate_pct: 0, more_than_pct: 0 },
      insider_activity: { buy_count: 1, sell_count: 0, last_transaction_date: "2026-08-13", net_direction: "net_buying" },
    });
    expect(buildFingerprint(withBoth, [])).toMatchObject({ lastSuspensionDate: "2026-01-10", insiderLastDate: "2026-08-13" });
    expect(buildFingerprint(stockData(), [])).toMatchObject({ lastSuspensionDate: null, insiderLastDate: null });
  });
});

describe("describeChanges", () => {
  const base: StockFingerprint = { watch: ["fall"], lastDividendExDate: "2026-05-05", lastAgmDate: null, lastRightsExDate: null, lastSplitDate: null, lastSuspensionDate: null, insiderLastDate: null };

  it("reports nothing when there is no baseline (never seen before)", () => {
    expect(describeChanges(null, base, {})).toEqual([]);
  });

  it("reports nothing when nothing changed", () => {
    expect(describeChanges(base, base, { fall: "Turun banyak" })).toEqual([]);
  });

  it("names a newly active watch item using its own current title", () => {
    const now: StockFingerprint = { ...base, watch: ["fall", "loss_year"] };
    expect(describeChanges(base, now, { fall: "Turun banyak", loss_year: "Perusahaan rugi" })).toEqual(["Perusahaan rugi"]);
  });

  it("does not re-report a watch item that was already active", () => {
    expect(describeChanges(base, base, { fall: "Turun banyak" })).toEqual([]);
  });

  it("reports a watch item that stopped being active as nothing (only additions matter)", () => {
    const now: StockFingerprint = { ...base, watch: [] };
    expect(describeChanges(base, now, {})).toEqual([]);
  });

  it("reports a new dated event, but not one that stayed the same", () => {
    const now: StockFingerprint = { ...base, lastAgmDate: "2026-09-10" };
    expect(describeChanges(base, now, {})).toEqual(["RUPS baru dijadwalkan"]);
    expect(describeChanges(base, { ...base }, {})).toEqual([]);
  });

  it("reports a changed dividend ex-date as a new dividend", () => {
    const now: StockFingerprint = { ...base, lastDividendExDate: "2026-09-01" };
    expect(describeChanges(base, now, {})).toEqual(["Dividen baru tercatat"]);
  });

  it("can report several changes at once, watch items first", () => {
    const now: StockFingerprint = { ...base, watch: ["fall", "recent_price_suspension"], lastSuspensionDate: "2026-09-11" };
    expect(describeChanges(base, now, { fall: "Turun banyak", recent_price_suspension: "Disuspensi karena lonjakan" })).toEqual(["Disuspensi karena lonjakan", "Disuspensi bursa"]);
  });
});
