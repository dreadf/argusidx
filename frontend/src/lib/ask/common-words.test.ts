import { describe, expect, it } from "vitest";
import { COMMON_WORDS, commonWordTickers } from "./common-words";
import { loadRealStocks } from "./tip-test-deps";

/**
 * Drift test. If a newly listed ticker is an ordinary word (or the word list
 * changes), this fails until a person reviews the change and updates the
 * expected set below. Reviewed against data/app/stocks.json (962 stocks).
 */
const REVIEWED_COMMON_WORD_TICKERS = [
  "AGAR", "AKSI", "AMAN", "ARTI", "AWAN", "AYAM", "BACA", "BAIK", "BAJA", "BALI", "BANK", "BAPA", "BATA", "BABY", "BEER",
  "BEEF", "BELI", "BEST", "BLUE", "BOAT", "BOLA", "BOSS", "BUAH", "BUKA", "BULL", "BUMI", "CARE", "CARS", "CASH", "CITY",
  "COAL", "COIN", "CUAN", "DATA", "DAYA", "DEAL", "DEWA", "DIGI", "ELIT", "EMAS", "ENAK", "FAST", "FILM", "FIRE", "FISH",
  "FOOD", "GOLD", "GOOD", "GULA", "GUNA", "HALO", "HERO", "HILL", "HITS", "HOME", "HOPE", "IDEA", "IKAN", "JAYA", "KAYU",
  "KEJU", "KING", "KIOS", "KOPI", "KOTA", "LABA", "LAJU", "LAND", "LEAD", "LIFE", "LINK", "LIVE", "LUCK", "MAHA", "MAIN",
  "MARI", "MEGA", "MEJA", "MINE", "NAIK", "NASI", "NICE", "NUSA", "OBAT", "PACK", "PADA", "PADI", "PALM", "PLAN", "PURE",
  "RAJA", "RATU", "REAL", "RISE", "ROCK", "RUNS", "SAFE", "SAME", "SATU", "SHIP", "SINI", "SOFA", "STAR", "SURE", "TAMU",
  "TAXI", "TECH", "TOOL", "TOYS", "TRUE", "TRUK", "UANG", "UNIT", "WIFI", "WINE", "WINS", "WOOD", "ZONE",
].sort();

describe("common-word tickers", () => {
  const codes = loadRealStocks().map((s) => s.code);

  it("matches the reviewed set (fails when a new common-word ticker appears)", () => {
    expect(commonWordTickers(codes)).toEqual(REVIEWED_COMMON_WORD_TICKERS);
  });

  it("includes the tickers named in the brief", () => {
    const set = new Set(commonWordTickers(codes));
    for (const c of ["BELI", "CUAN", "UANG", "EMAS", "BUMI", "BANK", "GOLD", "KOTA", "DAYA", "JAYA", "PADI", "NASI", "TAMU", "AMAN", "MARI"]) {
      expect(set.has(c)).toBe(true);
    }
  });

  it("word list is lowercase and free of duplicates", () => {
    expect(COMMON_WORDS.every((w) => w === w.toLowerCase())).toBe(true);
    expect(new Set(COMMON_WORDS).size).toBe(COMMON_WORDS.length);
  });

  it("a hypothetical new ticker that is a word is detected", () => {
    expect(commonWordTickers([...codes, "MAJU"])).toContain("MAJU");
    expect(commonWordTickers([...codes, "MAJU"])).not.toEqual(REVIEWED_COMMON_WORD_TICKERS);
    expect(commonWordTickers(["XQZV"])).toEqual([]);
  });
});
