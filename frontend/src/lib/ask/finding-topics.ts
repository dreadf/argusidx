import { escapeRegExp } from "./text-utils";

/**
 * Keyword → finding mapping, so a topical question ("apakah saham murah
 * lebih untung?") can surface the matching row(s) of the honesty
 * scoreboard (data/app/findings.json) without an LLM. Keyed by the exact
 * English `belief` string findings.json uses as its row identity (same
 * key pipeline/appdata/findings_translations.py matches on): never by
 * `belief_id`, which is Bahasa display text and could be edited without
 * this file's knowledge.
 *
 * A question may legitimately match more than one row (e.g. both payout
 * findings share "rasio pembayaran"): that's surfaced as multiple
 * findings, never collapsed into one, matching the no-combined-verdict
 * rule everywhere else findings are shown.
 *
 * Verified against the real, current `data/app/findings.json` (19 rows,
 * checked 2026-09-22): every `belief` string below is copied verbatim
 * from that file, not retyped from memory.
 */
export const FINDING_TOPIC_KEYWORDS: { belief: string; keywords: string[] }[] = [
  {
    belief: "Cheap stocks (low P/E) do better",
    keywords: ["p/e", "pe rendah", "valuasi murah", "saham murah", "price to earnings", "price-to-earnings"],
  },
  {
    belief: "High dividend yield means better returns",
    // Deliberately NOT the bare phrase "dividen tinggi" - it's a real
    // substring of payout-ratio questions too ("rasio pembayaran dividen
    // tinggi"), which mismatched this yield finding onto a payout-ratio
    // question during testing (2026-09-13). Kept specific to "yield".
    keywords: ["dividend yield", "yield dividen", "yield tinggi", "imbal hasil dividen"],
  },
  {
    belief: "Small companies earn more",
    keywords: ["perusahaan kecil", "small cap", "kapitalisasi kecil", "saham kecil"],
  },
  {
    belief: "Oversold (RSI < 30) means a bounce",
    keywords: ["oversold", "rsi", "memantul", "bounce", "jenuh jual"],
  },
  {
    belief: "Price above its 200-day average keeps going up",
    keywords: ["rata-rata 200 hari", "200 day", "200-day", "moving average"],
  },
  {
    belief: "Recent 60-day momentum predicts next month",
    keywords: ["momentum", "tren pergerakan", "60 hari"],
  },
  {
    belief: "High ROE (quality) predicts better returns",
    keywords: ["roe", "return on equity", "profitabilitas"],
  },
  {
    belief: "High leverage (debt/equity) predicts worse returns",
    keywords: ["utang", "leverage", "debt to equity", "debt-to-equity", "der"],
  },
  {
    belief: "A stock suspended for a sudden price spike keeps rising",
    keywords: ["disuspensi", "suspensi", "lonjakan harga"],
  },
  {
    belief: "Fast revenue growth predicts better returns",
    keywords: ["pertumbuhan pendapatan", "revenue growth", "pertumbuhan penjualan", "pertumbuhan bisnis"],
  },
  {
    belief: "High payout ratio predicts worse returns",
    keywords: ["rasio pembayaran", "payout ratio"],
  },
  {
    belief: "A high payout ratio predicts a dividend cut",
    keywords: ["pemotongan dividen", "dividend cut", "potong dividen", "pangkas dividen"],
  },
  {
    belief: "Combining a cheap/quality/leverage signal with a technical one beats either alone",
    keywords: ["gabungan sinyal", "kombinasi sinyal", "menggabungkan sinyal"],
  },
  {
    belief: "Thin float means wild swings",
    keywords: ["free float", "kepemilikan publik", "saham bergejolak", "float rendah"],
  },
  {
    belief: "Rising profits mean a rising share price",
    keywords: ["laba naik", "kenaikan laba", "pertumbuhan laba", "earnings growth", "profit growth", "laba bertumbuh"],
  },
  {
    belief: "Foreign investors buying heavily means the price will rise",
    keywords: ["asing borong", "asing beli", "asing masuk", "net buy asing", "foreign buy", "top foreign buy", "asing akumulasi", "foreign flow"],
  },
  {
    belief: "Insiders buying their own stock means the price will rise",
    keywords: ["orang dalam beli", "insider beli", "pembelian insider", "direksi beli", "komisaris beli", "insider buying", "insider buy"],
  },
  {
    belief: "Insiders selling before a price spike warns of a coming crash",
    keywords: ["penjualan insider", "jual insider", "insider selling", "orang dalam menjual", "aktivitas insider"],
  },
  {
    belief: "Positive news coverage predicts a stock will rise",
    keywords: ["berita positif", "sentimen berita", "berita bagus", "liputan berita", "news sentiment"],
  },
];

/** Word-boundary-safe, case-insensitive match against the question text:
 * plain `.includes()` would let a short keyword like "roe" match inside an
 * unrelated word ("heroes") or "der" inside "border"; `\b...\b` requires it
 * stand as its own word (or phrase, for multi-word keywords). Returns the
 * matching `belief` keys: 0, 1, or several. */
export function matchFindingTopics(text: string): string[] {
  return FINDING_TOPIC_KEYWORDS.filter((entry) =>
    entry.keywords.some((kw) => new RegExp(`\\b${escapeRegExp(kw)}\\b`, "i").test(text))
  ).map((entry) => entry.belief);
}
