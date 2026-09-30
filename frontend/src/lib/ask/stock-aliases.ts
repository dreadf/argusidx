/**
 * Curated short names people actually type for a listed stock that neither
 * its exact ticker nor its full registered company name would catch
 * (findStockInText and readTip already match both of those). "RSI BCA lagi
 * naik" names BBCA as plainly as "RSI BBCA lagi naik" would to a person,
 * but neither the ticker match (case-sensitive "BCA" != "BBCA") nor the
 * company-name match ("bank central asia" does not appear) catches it.
 *
 * Every entry is checked against data/app/stocks.json's actual
 * `company_name` (2026-09-30), not recalled from memory: some names have
 * changed since a ticker's old nickname was coined (ADRO is now "Alamtri
 * Resources Indonesia", not "Adaro Energy"; ACES is "Aspirasi Hidup
 * Indonesia", not "Ace Hardware"), so a plausible-sounding guess is left
 * out rather than shipped unverified.
 *
 * Deliberately short and all proper nouns: every key here carries the same
 * "not an ordinary word" bar common-words.ts sets for tickers, so a false
 * match on everyday text is not a risk this list can reintroduce.
 */
export const STOCK_ALIASES: Readonly<Record<string, string>> = {
  bca: "BBCA", // PT Bank Central Asia Tbk.
  bri: "BBRI", // PT Bank Rakyat Indonesia (Persero) Tbk
  bni: "BBNI", // PT Bank Negara Indonesia (Persero) Tbk
  btn: "BBTN", // PT Bank Tabungan Negara (Persero) Tbk
  bsi: "BRIS", // PT Bank Syariah Indonesia Tbk
  telkom: "TLKM", // PT Telkom Indonesia (Persero) Tbk
  gojek: "GOTO", // PT GoTo Gojek Tokopedia Tbk
  tokopedia: "GOTO",
  antam: "ANTM", // Aneka Tambang Tbk.
  indosat: "ISAT", // PT Indosat Tbk
};
