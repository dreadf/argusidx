import { describe, expect, it } from "vitest";
import { findStockInText } from "./stock-lookup";

/**
 * findStockInText reads data/app/stocks.json via stock-data.ts's real,
 * cached loader (the same one the app itself uses), not a test fixture:
 * these are integration tests against the real universe, same spirit as
 * tip-reader.test.ts's realDeps().
 */
describe("findStockInText", () => {
  it("resolves a curated alias (the reported case: BCA -> BBCA)", async () => {
    expect(await findStockInText("RSI BCA lagi naik, apakah akan turun")).toBe("BBCA");
  });

  it("resolves aliases case-insensitively", async () => {
    expect(await findStockInText("bagaimana kondisi bri sekarang?")).toBe("BBRI");
    expect(await findStockInText("BSI lagi oversold?")).toBe("BRIS");
  });

  it("still resolves the full company name", async () => {
    expect(await findStockInText("bagaimana kondisi Bank Central Asia?")).toBe("BBCA");
  });

  it("still resolves an exact, case-sensitive ticker", async () => {
    expect(await findStockInText("apa kabar BBCA hari ini")).toBe("BBCA");
  });

  it("does not let a lowercase alias-adjacent word misfire (word boundary holds)", async () => {
    // "bca" must not match inside an unrelated longer word.
    expect(await findStockInText("dia lagi sibuk banget")).toBeNull();
  });

  it("returns null, not a guess, for ordinary text", async () => {
    expect(await findStockInText("apakah harga akan naik besok?")).toBeNull();
  });
});
