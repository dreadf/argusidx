/**
 * Checked-in list of ordinary words (Bahasa Indonesia chat vocabulary plus
 * the English words that show up in tip messages). It exists for one job:
 * finding IDX tickers that are ALSO everyday words ("BELI", "CUAN", "BUMI"),
 * so tip-reader.ts never treats a bare occurrence of them as a stock.
 *
 * The list is a superset on purpose (it contains words that are not tickers
 * today). A ticker is a "common-word ticker" when its code, lowercased, is in
 * this list. `common-words.test.ts` pins the exact resulting set against
 * data/app/stocks.json, so a newly listed ticker that happens to be an
 * ordinary word fails that test until a person reviews it and either adds
 * the word here or accepts it in the test's expected set.
 */
export const COMMON_WORDS: readonly string[] = [
  // Indonesian: money, trading and chat vocabulary
  "beli", "jual", "cuan", "uang", "emas", "bumi", "bank", "kota", "daya", "jaya", "padi", "nasi", "tamu", "aman", "mari",
  "naik", "turun", "baik", "laba", "satu", "buka", "sini", "pada", "agar", "aksi", "arti", "awan", "ayam", "baca", "baja",
  "bali", "bapa", "bata", "bola", "buah", "dewa", "enak", "gula", "guna", "halo", "ikan", "kayu", "keju", "kopi", "laju",
  "main", "maju", "mega", "meja", "nusa", "obat", "palm", "raja", "ratu", "truk", "sofa", "elit", "maha", "kios", "wifi",
  "sehat", "lagi", "mulai", "pasti", "besok", "hari", "bulan", "tahun", "harga", "saham", "target", "sekarang",
  // English words common in tip messages
  "baby", "best", "cash", "city", "coal", "coin", "data", "deal", "digi", "fast", "film", "fire", "fish", "food", "gold",
  "good", "home", "hope", "idea", "land", "lead", "life", "link", "live", "luck", "mine", "pack", "plan", "real", "rise",
  "safe", "same", "sure", "taxi", "tech", "tool", "toys", "true", "unit", "zone", "boss", "bull", "hero", "star", "king",
  "wine", "wood", "blue", "beer", "beef", "boat", "care", "cars", "hill", "hits", "pure", "rock", "runs", "ship", "wins",
  "nice", "moon", "buy", "sell", "hold",
];

/** Tickers (bare codes, any case) whose lowercase form is an ordinary word. Sorted, upper-case. */
export function commonWordTickers(codes: readonly string[]): string[] {
  const words = new Set(COMMON_WORDS);
  return codes
    .map((c) => c.toUpperCase())
    .filter((c) => words.has(c.toLowerCase()))
    .sort();
}
