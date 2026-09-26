/**
 * Claim registry for the tip reader (tip-reader.ts). Pure data, no I/O.
 *
 * Three kinds of entry:
 *  - "belief": a wording that maps to a tested belief in data/app/findings.json.
 *    Keyed by the exact English `belief` string (same identity finding-topics.ts
 *    uses), never by display text. A belief that is not in the findings passed
 *    to readTip is returned as `pending`. H6 (foreign flow) is registered with
 *    pending: true because it is not in findings.json yet.
 *  - "situation": a circumstance the app has a base-rate page for.
 *  - "promotion": wording that is common in promotional messages. It yields
 *    only a neutral note. It is never a verdict on a stock or on the sender.
 *
 * Variants are lowercase regex sources, matched against text that
 * tip-reader.ts has lowercased and squeezed (3+ repeated letters collapse to
 * one, so "mantuuul" reads as "mantul"). No nested unbounded quantifiers.
 */

export type ClaimKind = "belief" | "situation" | "promotion";
export type SituationId = "spike" | "fall" | "ipo" | "suspension";
export type PromotionCategory = "certainty" | "urgency" | "target" | "secret";

export type ClaimTarget =
  | {
      type: "finding";
      /** Exact `belief` keys in findings.json. */
      beliefs: readonly string[];
      /** Research ids for findings that are not in findings.json yet (e.g. "H6"). */
      pendingIds: readonly string[];
    }
  | { type: "situation"; situation: SituationId; /** app/situasi slug, or null when no page exists. */ slug: string | null }
  | { type: "promotion"; category: PromotionCategory };

export interface ClaimDef {
  id: string;
  kind: ClaimKind;
  /** Short Bahasa label for the claim as the sender wrote it. */
  label: string;
  variants: readonly string[];
  target: ClaimTarget;
}

const B = {
  cheap: "Cheap stocks (low P/E) do better",
  yield: "High dividend yield means better returns",
  small: "Small companies earn more",
  oversold: "Oversold (RSI < 30) means a bounce",
  ma200: "Price above its 200-day average keeps going up",
  momentum: "Recent 60-day momentum predicts next month",
  roe: "High ROE (quality) predicts better returns",
  leverage: "High leverage (debt/equity) predicts worse returns",
  revenue: "Fast revenue growth predicts better returns",
  payout: "High payout ratio predicts worse returns",
  payoutCut: "A high payout ratio predicts a dividend cut",
  float: "Thin float means wild swings",
  profits: "Rising profits mean a rising share price",
  insider: "Insiders selling before a price spike warns of a coming crash",
  news: "Positive news coverage predicts a stock will rise",
} as const;

const finding = (beliefs: string[], pendingIds: string[] = []): ClaimTarget => ({ type: "finding", beliefs, pendingIds });

export const CLAIMS: readonly ClaimDef[] = [
  // (a) tested beliefs
  {
    id: "oversold-rsi",
    kind: "belief",
    label: "Oversold / akan memantul",
    variants: ["\\bover\\s?sol[d]{0,2}\\b", "\\bjenuh jual\\b", "\\bmantul\\w*", "\\bmemantul\\b", "\\bpantul\\w*", "\\brebound\\b", "\\bbounce\\b", "\\brsi\\b"],
    target: finding([B.oversold]),
  },
  {
    id: "valuasi-murah",
    kind: "belief",
    label: "Valuasi murah (P/E rendah)",
    variants: [
      "\\bp\\/?e(r)? (murah|rendah|kecil)\\b",
      "\\bper\\s?(murah|rendah|kecil)\\b",
      "\\bper\\s?(<|di ?bawah)\\s?\\d+",
      "\\bunder\\s?value[d]?\\b",
      "\\bvaluasi (masih )?(murah|rendah|menarik)\\b",
      "\\bsaham murah\\b",
    ],
    target: finding([B.cheap]),
  },
  {
    id: "dividen-tinggi",
    kind: "belief",
    label: "Dividen besar",
    variants: [
      "\\bdiv(iden|idend)? (gede|gd|besar|tinggi|jumbo|gemuk|fantastis)\\b",
      "\\b(dividend|dividen|div) yield\\b",
      "\\byield (tinggi|gede|besar)\\b",
      "\\bhigh dividend\\b",
      "\\bdiv(iden|idend)? \\d+([.,]\\d+)? ?%",
    ],
    target: finding([B.yield]),
  },
  {
    id: "payout-tinggi",
    kind: "belief",
    label: "Rasio pembayaran dividen tinggi",
    variants: ["\\bpayout( ratio)? (tinggi|gede|besar)\\b", "\\brasio (pembayaran|payout)\\b"],
    target: finding([B.payout, B.payoutCut]),
  },
  {
    id: "laba-naik",
    kind: "belief",
    label: "Laba naik",
    variants: [
      "\\blaba (bersih )?(naik|tumbuh|melonjak|meroket|bertumbuh)\\b",
      "\\blaba\\b.{0,20}\\bnaik terus\\b",
      "\\b(kenaikan|pertumbuhan) laba\\b",
      "\\bprofit (bersih )?(naik|tumbuh|melonjak)\\b",
      "\\bearnings? (naik|growth|tumbuh|bagus)\\b",
      "\\beps naik\\b",
      "\\bkinerja (keuangan )?(bagus|moncer|apik|kinclong)\\b",
      "\\blaporan keuangan (bagus|moncer|kinclong|oke|apik)\\b",
      "\\bnet profit (naik|growth)\\b",
    ],
    target: finding([B.profits]),
  },
  {
    id: "berita-positif",
    kind: "belief",
    label: "Berita atau sentimen positif",
    variants: [
      "\\bberita (bagus|positif|baik|bullish)\\b",
      "\\bsentimen\\b",
      "\\bkatalis\\b",
      "\\bkabar (baik|bagus|gembira)\\b",
      "\\bgood news\\b",
      "\\bpositive (news|sentiment)\\b",
    ],
    target: finding([B.news]),
  },
  {
    id: "tren-naik",
    kind: "belief",
    label: "Tren naik / breakout",
    variants: [
      "\\btren(d)? (naik|kuat|bagus|positif|menguat)\\b",
      "\\bup ?trend\\b",
      "\\bbreak ?out\\b",
      "\\btembus resist\\w*",
      "\\bbullish\\b",
      "\\b(terus naik|naik terus|naik melulu)\\b",
    ],
    target: finding([B.momentum, B.ma200]),
  },
  {
    id: "ma-200",
    kind: "belief",
    label: "Di atas rata-rata 200 hari / golden cross",
    variants: ["\\bgolden cross\\b", "\\bdi ?atas ma ?200\\b", "\\bma ?200\\b", "\\brata-?rata 200 hari\\b", "\\b200 ?(day|dma)\\b"],
    target: finding([B.ma200]),
  },
  {
    id: "momentum",
    kind: "belief",
    label: "Momentum harga",
    variants: ["\\bmomentum\\b"],
    target: finding([B.momentum]),
  },
  {
    id: "asing-borong",
    kind: "belief",
    label: "Asing borong / asing masuk",
    variants: [
      "\\basing (borong|masuk|beli|net ?buy|akumulasi|serbu|banjir)\\b",
      "\\b(investor|dana) asing (borong|masuk|mengalir)\\b",
      "\\bnet ?(foreign )?buy( asing)?\\b",
      "\\bnb asing\\b",
      "\\bforeign (inflow|buying|flow)\\b",
    ],
    target: finding([], ["H6"]),
  },
  {
    id: "roe-tinggi",
    kind: "belief",
    label: "ROE tinggi",
    variants: ["\\broe (tinggi|bagus|gede|besar)\\b", "\\bprofitabilitas tinggi\\b"],
    target: finding([B.roe]),
  },
  {
    id: "utang",
    kind: "belief",
    label: "Utang rendah / DER",
    variants: ["\\butang (kecil|rendah|tinggi|besar)\\b", "\\bder (rendah|kecil|tinggi)\\b", "\\bdebt (rendah|tinggi|kecil)\\b"],
    target: finding([B.leverage]),
  },
  {
    id: "pendapatan-naik",
    kind: "belief",
    label: "Pendapatan naik",
    variants: ["\\b(pendapatan|omzet|penjualan|revenue) (naik|tumbuh|melonjak)\\b", "\\brevenue growth\\b"],
    target: finding([B.revenue]),
  },
  {
    id: "float-tipis",
    kind: "belief",
    label: "Float tipis",
    variants: ["\\b(free )?float (tipis|kecil|rendah)\\b", "\\bsaham tipis\\b"],
    target: finding([B.float]),
  },
  {
    id: "saham-kecil",
    kind: "belief",
    label: "Perusahaan kecil",
    variants: ["\\bsmall ?cap\\b", "\\bsaham kecil\\b", "\\bperusahaan kecil\\b", "\\bkapitalisasi kecil\\b"],
    target: finding([B.small]),
  },
  {
    id: "insider-jual",
    kind: "belief",
    label: "Penjualan oleh orang dalam",
    variants: ["\\binsider (jual|selling|menjual)\\b", "\\b(direksi|komisaris) (jual|menjual)\\b", "\\borang dalam (jual|menjual)\\b"],
    target: finding([B.insider]),
  },

  // (b) situations
  {
    id: "situasi-lonjak",
    kind: "situation",
    label: "Harga melonjak",
    variants: [
      "\\blonjak\\w*",
      "\\bmelonjak\\b",
      "\\bara\\b",
      "\\bauto reject atas\\b",
      "\\bnaik gila[- ]?gila(an|2an)\\b",
      "\\bgila2an\\b",
      "\\bnaik gila\\b",
      "\\b(terbang|meroket|melesat)\\b",
      "\\bnaik (tajam|drastis|pesat)\\b",
      "\\bgap up\\b",
    ],
    target: { type: "situation", situation: "spike", slug: null },
  },
  {
    id: "situasi-turun",
    kind: "situation",
    label: "Harga turun banyak",
    variants: [
      "\\bturun (banyak|dalam|tajam|drastis|parah)\\b",
      "\\b(anjlok|longsor|jeblok|merosot|ambles|rontok)\\b",
      "\\barb\\b",
      "\\bauto reject bawah\\b",
      "\\bdiskon\\b",
      "\\bnyangkut\\b",
      "\\bfloating loss\\b",
    ],
    target: { type: "situation", situation: "fall", slug: "turun-banyak" },
  },
  {
    id: "situasi-ipo",
    kind: "situation",
    label: "IPO",
    variants: ["\\bipo\\b", "\\blisting perdana\\b", "\\bbaru listing\\b", "\\bpenawaran umum perdana\\b"],
    target: { type: "situation", situation: "ipo", slug: "ikut-ipo" },
  },
  {
    id: "situasi-suspensi",
    kind: "situation",
    label: "Habis suspensi",
    variants: [
      "\\b(habis|abis|baru) (di)?suspen[sd]\\w*",
      "\\bsuspen[sd]\\w*",
      "\\bunsuspend\\b",
      "\\bkena suspen\\w*",
    ],
    target: { type: "situation", situation: "suspension", slug: "pernah-disuspensi" },
  },

  // (c) promotion wording (neutral note only)
  {
    id: "janji-pasti",
    kind: "promotion",
    label: "Kata kepastian",
    variants: [
      "\\bpasti\\b",
      "\\bdijamin\\b",
      "\\bgaransi\\b",
      "\\bguarantee[d]?\\b",
      "\\b100 ?%",
      "\\bauto (cuan|profit|kaya)\\b",
      "\\bto the moon\\b",
      "\\btanpa risiko\\b",
      "\\bno risk\\b",
      "\\bbebas rugi\\b",
      "\\banti rugi\\b",
      "\\bsure profit\\b",
    ],
    target: { type: "promotion", category: "certainty" },
  },
  {
    id: "desakan-waktu",
    kind: "promotion",
    label: "Desakan waktu",
    variants: [
      "\\bburuan\\b",
      "\\bsebelum (terlambat|telat|keduluan|naik)\\b",
      "\\bjangan sampai (ketinggalan|nyesel|menyesal)\\b",
      "\\bkesempatan terakhir\\b",
      "\\blast call\\b",
      "\\bhari ini saja\\b",
      "\\bfomo\\b",
      "\\bcepat (masuk|gabung)\\b",
    ],
    target: { type: "promotion", category: "urgency" },
  },
  {
    id: "target-harga",
    kind: "promotion",
    label: "Target harga / kelipatan",
    variants: [
      "\\b(tp|tgt|target)( harga)? ?[:@=]? ?\\d",
      "\\btarget( harga)? (x|\\d+ ?x|\\d+ ?kali|double)",
      "\\b\\d+ ?x (lipat|lagi)\\b",
      "\\bx\\d+\\b",
      "\\blipat ganda\\b",
    ],
    target: { type: "promotion", category: "target" },
  },
  {
    id: "info-rahasia",
    kind: "promotion",
    label: "Informasi rahasia",
    variants: [
      "\\binfo orang dalam\\b",
      "\\binfo dari dalam\\b",
      "\\borang dalam\\b",
      "\\bbocoran\\b",
      "\\bbandar (masuk|akumulasi|lagi|mulai)\\b",
      "\\binside[r]? info\\b",
      "\\binfo (valid|a1|rahasia)\\b",
    ],
    target: { type: "promotion", category: "secret" },
  },
];

export const PROMOTION_NOTES: Record<PromotionCategory, string> = {
  certainty: "Kata-kata yang menjanjikan kepastian hasil banyak dipakai dalam pesan promosi. Hasil investasi tidak pernah pasti.",
  urgency: "Desakan waktu (\"buruan\", \"sebelum terlambat\") banyak dipakai dalam pesan promosi.",
  target: "Target harga atau kelipatan (\"TP\", \"2x\") banyak dipakai dalam pesan promosi. Target itu tidak diuji di sini.",
  secret: "Klaim informasi orang dalam atau bocoran banyak dipakai dalam pesan promosi. Kami tidak bisa memeriksa sumbernya.",
};

export const PROMOTION_GUIDANCE =
  "Frasa di atas tidak membuktikan apa pun tentang saham atau pengirimnya. Panduan OJK Waspada Investasi: cek \"2L: Legal dan Logis\", yaitu izin pihak yang menawarkan dan kewajaran imbal hasilnya.";

/** Fixed checklist, shown for every tip; not derived from the message. */
export const SENDER_QUESTIONS: readonly string[] = [
  "Siapa pengirim pesan ini, dan apa dasar informasinya?",
  "Adakah sumber yang bisa diperiksa sendiri, seperti laporan keuangan atau keterbukaan informasi BEI?",
  "Apakah pengirim atau grupnya punya kepentingan pada saham ini, misalnya sudah memegangnya?",
  "Berapa kemungkinan rugi yang disebutkan, dan apa yang membuat perkiraan pengirim bisa meleset?",
  "Apakah pihak yang menawarkan terdaftar dan berizin di OJK, dan apakah imbal hasil yang dijanjikan masuk akal?",
];

let compiled: { def: ClaimDef; res: RegExp[] }[] | null = null;

/** Compiled (non-global, so no lastIndex state) variants, built once. */
export function compiledClaims(): { def: ClaimDef; res: RegExp[] }[] {
  if (!compiled) compiled = CLAIMS.map((def) => ({ def, res: def.variants.map((v) => new RegExp(v, "i")) }));
  return compiled;
}
