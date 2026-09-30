import { describe, expect, it } from "vitest";
import { COMMON_WORDS } from "./common-words";
import { STOCK_ALIASES } from "./stock-aliases";
import { loadRealStocks } from "./tip-test-deps";

/**
 * Drift test: every alias must point at a ticker that is actually listed
 * today, and every key must still be lowercase and free of collisions with
 * common-words.ts (an alias that is also an ordinary word would reintroduce
 * the exact false-positive class common-words.ts exists to prevent).
 */
describe("stock aliases", () => {
  const codes = new Set(loadRealStocks().map((s) => s.code));

  it("every alias target is a real, currently listed ticker", () => {
    for (const [alias, code] of Object.entries(STOCK_ALIASES)) {
      expect(codes.has(code), `${alias} -> ${code} (not in data/app/stocks.json)`).toBe(true);
    }
  });

  it("keys are lowercase, at least 3 letters, and unique", () => {
    const keys = Object.keys(STOCK_ALIASES);
    for (const k of keys) {
      expect(k).toBe(k.toLowerCase());
      expect(k.length).toBeGreaterThanOrEqual(3);
    }
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("no alias is also an ordinary word (the module's own guarantee, checked, not assumed)", () => {
    // tip-reader.ts lets an alias match as a bare single word, bypassing the
    // multi-word guard company-name cores need for exactly this reason: a
    // key that turned out to be an everyday word would reintroduce the
    // false-positive class common-words.ts exists to prevent.
    const commonWords = new Set(COMMON_WORDS);
    for (const alias of Object.keys(STOCK_ALIASES)) {
      expect(commonWords.has(alias), `"${alias}" is in common-words.ts, unsafe as a bare-word alias`).toBe(false);
    }
  });
});
