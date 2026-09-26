import { describe, expect, it } from "vitest";
import { containsAdviceLanguage } from "./advice-language-guard";
import { CLAIMS, PROMOTION_GUIDANCE, PROMOTION_NOTES, SENDER_QUESTIONS } from "./tip-claims";
import { MAX_STOCKS, MAX_TIP_CHARS, readTip, type TipDeps, type TipReading } from "./tip-reader";
import { loadRealFindings, realDeps } from "./tip-test-deps";

const deps = realDeps();
const codes = (r: TipReading) => r.stocks.map((s) => s.code);
const claimIds = (r: TipReading) => r.claims.map((c) => c.id);
const promoCats = (r: TipReading) => r.promotionNotes.map((n) => n.category);

interface Case {
  name: string;
  text: string;
  stocks?: string[];
  ambiguous?: string[];
  claims?: string[];
  promo?: string[];
}

const CASES: Case[] = [
  { name: "plain ticker, all caps", text: "BBCA LAGI DISKON GAN, WAJIB PANTAU", stocks: ["BBCA"], claims: ["situasi-turun"] },
  { name: "dollar prefix", text: "$BBRI dividen gede tahun ini", stocks: ["BBRI"], claims: ["dividen-tinggi"] },
  { name: "hash prefix", text: "#TLKM oversold banget, RSI 25", stocks: ["TLKM"], claims: ["oversold-rsi"] },
  { name: ".JK suffix", text: "ASII.JK breakout resistance hari ini", stocks: ["ASII"], claims: ["tren-naik"] },
  { name: "lowercase ticker", text: "bbca sama bbri lagi murah per rendah", stocks: ["BBCA", "BBRI"], claims: ["valuasi-murah"] },
  { name: "mixed case", text: "Tlkm dan AsII katanya laba naik terus", stocks: ["TLKM", "ASII"], claims: ["laba-naik"] },
  { name: "emoji everywhere", text: "🚀🚀🚀 $GOTO 🔥🔥 to the moon 🌕 target 2x!!!", stocks: ["GOTO"], promo: ["certainty", "target"] },
  { name: "repeated punctuation", text: "BBCA!!!!!!! NAIK TERUS?????? ....", stocks: ["BBCA"], claims: ["tren-naik"] },
  { name: "several tickers", text: "Watchlist: BBCA BBRI BMRI BBNI ANTM", stocks: ["BBCA", "BBRI", "BMRI", "BBNI", "ANTM"] },
  { name: "no ticker, only claim", text: "saham yang oversold biasanya mantul", stocks: [], claims: ["oversold-rsi"] },
  { name: "no ticker, chit-chat", text: "selamat pagi semua, semoga hari ini lancar ya", stocks: [] },
  { name: "brief regression: BELI BUMI", text: "BELI BUMI SEKARANG!! TP 200 CUAN PASTI", stocks: ["BUMI"], ambiguous: ["BELI", "CUAN"], promo: ["certainty", "target"] },
  { name: "common word ticker only, bare", text: "BUMI LAGI TIDUR", stocks: [], ambiguous: ["BUMI"] },
  { name: "common word only, with saham", text: "saham BUMI lagi tidur", stocks: ["BUMI"] },
  { name: "common word only, emiten", text: "emiten CUAN naik ke 9000", stocks: ["CUAN"] },
  { name: "common word, price next to it", text: "GOLD 3500 tembus resist", stocks: ["GOLD"], claims: ["tren-naik"] },
  { name: "common word, dollar", text: "cek $EMAS sebelum terlambat", stocks: ["EMAS"], promo: ["urgency"] },
  { name: "common word, company name", text: "Bank Central Asia lapor laba naik", stocks: ["BBCA"], claims: ["laba-naik"] },
  { name: "ordinary Indonesian sentence, lowercase", text: "uang saya habis, mau beli nasi di kota", stocks: [], ambiguous: [] },
  { name: "ordinary sentence, caps", text: "AMAN GAN UANG BUAT BELI NASI", stocks: [], ambiguous: ["AMAN", "UANG", "BELI", "NASI"] },
  { name: "quantity is not a price", text: "UANG 500 JUTA HILANG", stocks: [], ambiguous: ["UANG"] },
  { name: "English mix", text: "Buy BBRI now, strong momentum, will go to the moon guaranteed", stocks: ["BBRI"], claims: ["momentum"], promo: ["certainty"] },
  { name: "English only, no ticker", text: "This is a sure thing, guaranteed 100% returns, no risk", stocks: [], promo: ["certainty"] },
  { name: "secret info", text: "Info orang dalam: bandar masuk ke ANTM minggu ini, bocoran valid", stocks: ["ANTM"], promo: ["secret"] },
  { name: "urgency", text: "Buruan masuk sebelum terlambat, jangan sampai ketinggalan!", stocks: [], promo: ["urgency"] },
  { name: "target multiples", text: "TP 3x lipat, target harga 5000", stocks: [], promo: ["target"] },
  { name: "foreign flow pending", text: "asing borong BBCA 3 hari berturut-turut", stocks: ["BBCA"], claims: ["asing-borong"] },
  { name: "foreign flow variant", text: "Asing masuk deras ke BMRI", stocks: ["BMRI"], claims: ["asing-borong"] },
  { name: "news", text: "BBRI berita bagus, sentimen positif dari analis", stocks: ["BBRI"], claims: ["berita-positif"] },
  { name: "value slang", text: "TLKM undervalued banget, PER murah", stocks: ["TLKM"], claims: ["valuasi-murah"] },
  { name: "dividend slang", text: "dividen gede BBNI, yield tinggi", stocks: ["BBNI"], claims: ["dividen-tinggi"] },
  { name: "spike", text: "ANTM ARA lagi, naik gila-gilaan hari ini", stocks: ["ANTM"], claims: ["situasi-lonjak"] },
  { name: "spike typo", text: "GOTO naik gila2an gaes, melonjak", stocks: ["GOTO"], claims: ["situasi-lonjak"] },
  { name: "fall", text: "BBCA turun banyak minggu ini, lagi diskon", stocks: ["BBCA"], claims: ["situasi-turun"] },
  { name: "IPO", text: "IPO baru listing perdana, hati-hati", stocks: [], claims: ["situasi-ipo"] },
  { name: "after suspension", text: "ANTM habis suspend, katanya bakal terbang", stocks: ["ANTM"], claims: ["situasi-suspensi", "situasi-lonjak"] },
  { name: "typo squeeze", text: "TLKM mantuuuul banget, oversoold", stocks: ["TLKM"], claims: ["oversold-rsi"] },
  { name: "golden cross", text: "BBRI golden cross, di atas MA200", stocks: ["BBRI"], claims: ["ma-200"] },
  { name: "unknown claim only", text: "katanya pemilik barunya artis terkenal dan pabriknya mau pindah ke luar negeri", stocks: [] },
  { name: "unknown four-letter word", text: "XYZW ABCD naik", stocks: [] },
  { name: "whatsapp forward", text: "*INFO SAHAM* 📢\n\n$BBCA\nTP: 10000\nSL: 8500\n\nBandar masuk!!! Buruan!!!", stocks: ["BBCA"], promo: ["target", "secret", "urgency"] },
  { name: "telegram multi-line", text: "Sinyal hari ini:\n1. BBRI entry 4500\n2. TLKM entry 3200\n3. ASII entry 5000", stocks: ["BBRI", "TLKM", "ASII"] },
  { name: "company name with ticker", text: "Bumi Resources kabarnya laba naik", stocks: ["BUMI"], claims: ["laba-naik"] },
  { name: "words containing tickers", text: "bumiputra dan bankir dan emasan", stocks: [], ambiguous: [] },
  { name: "ticker inside longer token", text: "XBBCAX BBCAA", stocks: [] },
  { name: "empty", text: "", stocks: [] },
  { name: "whitespace only", text: "   \n\n\t  ", stocks: [] },
  { name: "punctuation only", text: "?!?!?! ... ---", stocks: [] },
  { name: "emoji only", text: "🚀🚀🚀🔥🔥💰💰", stocks: [] },
  { name: "fullwidth characters", text: "＄ＢＢＣＡ　ｎａｉｋ", stocks: ["BBCA"] },
  { name: "insider claim", text: "direksi jual saham sebelum naik, insider jual", stocks: [], claims: ["insider-jual"] },
];

describe("readTip: realistic tip messages", () => {
  it("has at least 40 cases", () => {
    expect(CASES.length).toBeGreaterThanOrEqual(40);
  });

  for (const c of CASES) {
    it(c.name, () => {
      const r = readTip(c.text, deps);
      if (c.stocks) expect(codes(r)).toEqual(c.stocks);
      if (c.ambiguous) expect(r.ambiguous.map((a) => a.code)).toEqual(c.ambiguous);
      if (c.claims) expect(claimIds(r)).toEqual(expect.arrayContaining(c.claims));
      if (c.promo) expect(promoCats(r)).toEqual(expect.arrayContaining(c.promo));
    });
  }
});

describe("readTip: regressions", () => {
  it("'apakah harga akan naik?' matches no stock and offers no chip", () => {
    const r = readTip("apakah harga akan naik?", deps);
    expect(r.stocks).toEqual([]);
    expect(r.ambiguous).toEqual([]);
  });

  it("'APAKAH HARGA AKAN NAIK?' in caps is only an ambiguous NAIK, never a match", () => {
    const r = readTip("APAKAH HARGA AKAN NAIK?", deps);
    expect(r.stocks).toEqual([]);
  });

  it("BELI BUMI SEKARANG!! TP 200 CUAN PASTI: BUMI only, with context", () => {
    const r = readTip("BELI BUMI SEKARANG!! TP 200 CUAN PASTI", deps);
    expect(r.stocks).toHaveLength(1);
    expect(r.stocks[0]).toMatchObject({ code: "BUMI", matchedBy: "price-context" });
    expect(codes(r)).not.toContain("BELI");
    expect(codes(r)).not.toContain("CUAN");
    expect(r.ambiguous.map((a) => a.prompt)).toEqual(["Maksud Anda saham BELI?", "Maksud Anda saham CUAN?"]);
  });

  it("bare BUMI asks 'Maksud Anda saham BUMI?'", () => {
    const r = readTip("BUMI mau naik lagi nih", deps);
    expect(r.stocks).toEqual([]);
    expect(r.ambiguous).toEqual([{ code: "BUMI", companyName: expect.stringContaining("Bumi"), prompt: "Maksud Anda saham BUMI?" }]);
  });

  it("matched-by reason is the strongest available", () => {
    const r = readTip("saham BUMI, lalu $BUMI, lalu bumi resources", deps);
    expect(r.stocks).toHaveLength(1);
    expect(r.stocks[0].matchedBy).toBe("symbol-marker");
  });

  it("a longer company name is not read as a shorter one", () => {
    const r = readTip("Bumi Resources Minerals lagi rame", deps);
    expect(codes(r)).toEqual(["BRMS"]);
  });

  it("company name hides its inner word from the ticker scan", () => {
    const r = readTip("Bank Central Asia", deps);
    expect(codes(r)).toEqual(["BBCA"]);
    expect(r.ambiguous).toEqual([]);
  });

  it("the H6 claim is pending and points at H6", () => {
    const r = readTip("asing borong BBCA", deps);
    const claim = r.claims.find((c) => c.id === "asing-borong")!;
    expect(claim.target).toEqual({ type: "finding", findings: [{ ref: "H6", pending: true, hypothesisIds: ["H6"] }] });
  });

  it("belief claims resolve to real findings with their hypothesis ids", () => {
    const r = readTip("laba naik terus", deps);
    const claim = r.claims.find((c) => c.id === "laba-naik")!;
    expect(claim.target).toEqual({
      type: "finding",
      findings: [{ ref: "Rising profits mean a rising share price", pending: false, hypothesisIds: ["H17"] }],
    });
  });

  it("a belief missing from the injected findings is returned as pending, not dropped", () => {
    const r = readTip("laba naik terus", { stocks: deps.stocks, findings: [] });
    const t = r.claims[0].target;
    expect(t.type === "finding" && t.findings[0].pending).toBe(true);
  });

  it("news wording maps to the news finding (H9)", () => {
    const r = readTip("berita bagus", deps);
    const t = r.claims[0].target;
    expect(t.type === "finding" && t.findings[0].hypothesisIds).toEqual(["H9"]);
  });

  it("trend wording maps to both momentum and 200-day findings", () => {
    const r = readTip("trend naik", deps);
    const t = r.claims[0].target;
    expect(t.type === "finding" && t.findings.map((f) => f.hypothesisIds)).toEqual([["H14"], ["H14"]]);
  });

  it("situations carry the situasi slug when one exists", () => {
    expect(readTip("lagi diskon", deps).claims[0].target).toEqual({ type: "situation", situation: "fall", slug: "turun-banyak" });
    expect(readTip("ARA terus", deps).claims[0].target).toEqual({ type: "situation", situation: "spike", slug: null });
  });

  it("sentences without a known claim are listed, sentences with one are not", () => {
    const r = readTip("Pabriknya mau pindah ke luar negeri. BBCA laba naik terus.", deps);
    expect(r.unmatchedFragments).toEqual(["Pabriknya mau pindah ke luar negeri"]);
  });

  it("promotion wording yields a neutral note and OJK guidance, never a stock claim", () => {
    const r = readTip("PASTI CUAN 100%, TP 300, buruan!", deps);
    expect(r.promotionNotes.map((n) => n.category)).toEqual(["certainty", "urgency", "target"]);
    expect(r.promotionGuidance).toBe(PROMOTION_GUIDANCE);
    expect(PROMOTION_GUIDANCE).toContain("2L: Legal dan Logis");
    expect(PROMOTION_GUIDANCE).toContain("OJK");
    expect(r.claims).toEqual([]);
  });

  it("no promotion wording means no guidance", () => {
    const r = readTip("BBCA laba naik", deps);
    expect(r.promotionNotes).toEqual([]);
    expect(r.promotionGuidance).toBeNull();
  });

  it("always returns the fixed sender checklist", () => {
    expect(readTip("", deps).senderQuestions).toEqual(SENDER_QUESTIONS);
    expect(readTip("BBCA", deps).senderQuestions).toEqual(SENDER_QUESTIONS);
  });

  it("has no score or verdict field", () => {
    const keys = Object.keys(readTip("BBCA pasti naik", deps)).join(" ").toLowerCase();
    expect(keys).not.toMatch(/score|verdict|rating|risk|skor/);
  });
});

describe("readTip: limits", () => {
  it("returns at most 5 stocks and flags overflow", () => {
    const r = readTip("BBCA BBRI BMRI BBNI ANTM TLKM ASII GOTO", deps);
    expect(r.stocks).toHaveLength(MAX_STOCKS);
    expect(r.stocksOverflow).toBe(true);
    expect(r.stocksFound).toBe(8);
    expect(codes(r)).toEqual(["BBCA", "BBRI", "BMRI", "BBNI", "ANTM"]);
    expect(r.notices.join(" ")).toContain("8 saham");
  });

  it("exactly 5 stocks is not overflow", () => {
    const r = readTip("BBCA BBRI BMRI BBNI ANTM", deps);
    expect(r.stocksOverflow).toBe(false);
  });

  it("truncates input over 2,000 characters and flags it", () => {
    const text = `${"a".repeat(1990)} BBCA ${"b".repeat(100)} BBRI`;
    const r = readTip(text, deps);
    expect(r.truncated).toBe(true);
    expect(r.originalLength).toBe(text.length);
    expect(r.analyzedLength).toBe(MAX_TIP_CHARS);
    expect(r.notices.join(" ")).toContain("2.000");
    // "BBCA" straddles nothing here (start 1991) and BBRI is beyond the cut
    expect(codes(r)).toEqual(["BBCA"]);
  });

  it("does not read a ticker that sits after the cap", () => {
    const r = readTip(`${" ".repeat(MAX_TIP_CHARS)}BBCA`, deps);
    expect(r.truncated).toBe(true);
    expect(r.stocks).toEqual([]);
  });

  it("exactly 2,000 characters is not truncated", () => {
    const r = readTip("x".repeat(MAX_TIP_CHARS), deps);
    expect(r.truncated).toBe(false);
  });

  it("does not split a surrogate pair at the cut", () => {
    const text = `${"a".repeat(MAX_TIP_CHARS - 1)}🚀🚀`;
    const r = readTip(text, deps);
    expect(r.truncated).toBe(true);
    expect(r.analyzedLength).toBe(MAX_TIP_CHARS - 1);
  });

  it("a 2,000+ character realistic message still reads the early part", () => {
    const text = `$BBCA oversold, dividen gede!! ${"Info orang dalam, buruan sebelum terlambat. ".repeat(60)}`;
    expect(text.length).toBeGreaterThan(2000);
    const r = readTip(text, deps);
    expect(r.truncated).toBe(true);
    expect(codes(r)).toEqual(["BBCA"]);
    expect(claimIds(r)).toEqual(expect.arrayContaining(["oversold-rsi", "dividen-tinggi"]));
    expect(promoCats(r)).toEqual(expect.arrayContaining(["urgency", "secret"]));
  });

  it("caps fragments and their length", () => {
    const text = Array.from({ length: 30 }, (_, i) => `pabrik nomor ${i} dekat pelabuhan besar`).join(". ");
    const r = readTip(text, deps);
    expect(r.unmatchedFragments.length).toBeLessThanOrEqual(8);
    expect(r.unmatchedFragments.every((f) => f.length <= 140)).toBe(true);
    const long = readTip(`${"kata ".repeat(100)}selesai`, deps);
    expect(long.unmatchedFragments[0].length).toBeLessThanOrEqual(140);
  });
});

describe("readTip: stress and adversarial input", () => {
  it("handles a 10,000-character input quickly", () => {
    const text = "BBCA $BUMI #TLKM pasti naik!!! 🚀 TP 200 buruan sebelum terlambat, info orang dalam. ".repeat(130);
    expect(text.length).toBeGreaterThan(10_000);
    const start = Date.now();
    const r = readTip(text, deps);
    expect(Date.now() - start).toBeLessThan(1000);
    expect(r.truncated).toBe(true);
    expect(r.analyzedLength).toBe(MAX_TIP_CHARS);
    expect(r.stocks.length).toBeLessThanOrEqual(MAX_STOCKS);
  });

  it("does not backtrack badly on pathological input", () => {
    const inputs = ["a".repeat(10_000), "!".repeat(10_000), "laba ".repeat(2000), "tp ".repeat(3000), "$".repeat(5000), "BBCA.".repeat(2000), "asing ".repeat(2000)];
    for (const text of inputs) {
      const start = Date.now();
      readTip(text, deps);
      expect(Date.now() - start).toBeLessThan(1000);
    }
  });

  it("survives odd characters", () => {
    for (const text of ["\u0000\u0001BBCA\u0007", "BBCA‍‍NAIK", "𝐁𝐁𝐂𝐀", "\uD83D", "\uDE80BBCA", "ＢＢＣＡ.ＪＫ", "\r\n\r\nBBCA\r\n"]) {
      expect(() => readTip(text, deps)).not.toThrow();
    }
    expect(codes(readTip("\r\n\r\nBBCA\r\n", deps))).toEqual(["BBCA"]);
    expect(codes(readTip("ＢＢＣＡ.ＪＫ", deps))).toEqual(["BBCA"]);
  });

  it("tolerates non-string input without throwing", () => {
    expect(() => readTip(undefined as unknown as string, deps)).not.toThrow();
    expect(readTip(null as unknown as string, deps).stocks).toEqual([]);
  });
});

describe("readTip: properties", () => {
  // Deterministic pseudo-random generator (mulberry32) so failures reproduce.
  function rng(seed: number) {
    return () => {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const PIECES = [
    "BBCA", "bbri", "$TLKM", "#ASII", "GOTO.JK", "BUMI", "CUAN", "BELI", "NAIK", "saham", "emiten", "TP", "200", "target", "pasti", "dijamin",
    "oversold", "laba naik", "asing borong", "dividen gede", "🚀", "!!!", "???", "\n", ".", "buruan", "info orang dalam", "sekarang", "ANTM", "BMRI",
    "BBNI", "GOLD", "EMAS", "UANG", "ARA", "IPO", "diskon", "trend naik", "berita bagus", "Bank Central Asia", "harga", "akan", "turun", "besok",
  ];
  function randomTip(next: () => number): string {
    const n = 1 + Math.floor(next() * 60);
    let s = "";
    for (let i = 0; i < n; i++) s += PIECES[Math.floor(next() * PIECES.length)] + (next() < 0.8 ? " " : "");
    return s;
  }
  const tips = (() => {
    const next = rng(20260926);
    return Array.from({ length: 400 }, () => randomTip(next));
  })();

  function ourCopy(r: TipReading): string[] {
    return [
      ...r.notices,
      ...r.senderQuestions,
      ...r.ambiguous.map((a) => a.prompt),
      ...r.promotionNotes.map((n) => n.note),
      ...(r.promotionGuidance ? [r.promotionGuidance] : []),
      ...r.claims.map((c) => c.label),
    ];
  }

  it("is deterministic", () => {
    for (const t of tips) expect(readTip(t, deps)).toEqual(readTip(t, deps));
  });

  it("never returns more than 5 stock cards or 5 chips", () => {
    for (const t of tips) {
      const r = readTip(t, deps);
      expect(r.stocks.length).toBeLessThanOrEqual(5);
      expect(r.ambiguous.length).toBeLessThanOrEqual(5);
      expect(r.stocksOverflow).toBe(r.stocksFound > 5);
    }
  });

  it("never lets a stock be both matched and ambiguous, and never repeats a code", () => {
    for (const t of tips) {
      const r = readTip(t, deps);
      const matched = new Set(codes(r));
      expect(matched.size).toBe(r.stocks.length);
      for (const a of r.ambiguous) expect(matched.has(a.code)).toBe(false);
    }
  });

  it("never puts advice language in our own copy", () => {
    for (const t of tips) for (const line of ourCopy(readTip(t, deps))) expect(containsAdviceLanguage(line), line).toBe(false);
  });

  it("does not mutate its input or its dependencies", () => {
    const frozen: TipDeps = {
      stocks: Object.freeze(deps.stocks.map((s) => Object.freeze({ ...s }))),
      findings: Object.freeze(loadRealFindings().map((f) => Object.freeze({ ...f }))),
    };
    const snapshot = JSON.stringify(frozen);
    for (const t of tips.slice(0, 100)) {
      const copy = t.slice();
      readTip(t, frozen);
      expect(t).toBe(copy);
    }
    expect(JSON.stringify(frozen)).toBe(snapshot);
  });

  it("returns a fresh result each call (mutating one does not affect the next)", () => {
    const a = readTip("BBCA laba naik", deps);
    a.stocks.pop();
    a.claims.pop();
    const b = readTip("BBCA laba naik", deps);
    expect(codes(b)).toEqual(["BBCA"]);
    expect(claimIds(b)).toEqual(["laba-naik"]);
  });

  it("a common-word ticker is never matched without strong context", () => {
    const common = ["BELI", "CUAN", "UANG", "EMAS", "BUMI", "BANK", "GOLD", "KOTA", "DAYA", "JAYA", "PADI", "NASI", "TAMU", "AMAN", "MARI"];
    for (const c of common) {
      for (const text of [c, c.toLowerCase(), `${c} ${c}`, `ayo ${c} lagi`, `${c}!!!`, `${c}?`, `mau ${c} apa`]) {
        expect(readTip(text, deps).stocks, text).toEqual([]);
      }
      for (const text of [`$${c}`, `#${c}`, `${c}.JK`, `saham ${c}`, `emiten ${c}`, `${c} @100`, `${c} TP 500`]) {
        expect(codes(readTip(text, deps)), text).toEqual([c]);
      }
    }
  });
});

describe("our copy", () => {
  it("every registry note, guidance and checklist line passes the advice guard", () => {
    const lines = [...Object.values(PROMOTION_NOTES), PROMOTION_GUIDANCE, ...SENDER_QUESTIONS, ...CLAIMS.map((c) => c.label)];
    for (const line of lines) expect(containsAdviceLanguage(line), line).toBe(false);
  });

  it("the sender checklist is fixed at five questions", () => {
    expect(SENDER_QUESTIONS).toHaveLength(5);
  });
});

describe("claim registry", () => {
  const beliefs = new Set(loadRealFindings().map((f) => f.belief));

  it("has unique ids and at least one variant each", () => {
    expect(new Set(CLAIMS.map((c) => c.id)).size).toBe(CLAIMS.length);
    for (const c of CLAIMS) expect(c.variants.length).toBeGreaterThan(0);
  });

  it("every belief target exists verbatim in findings.json", () => {
    for (const c of CLAIMS) {
      if (c.target.type !== "finding") continue;
      for (const b of c.target.beliefs) expect(beliefs.has(b), `${c.id}: ${b}`).toBe(true);
    }
  });

  it("H6 is registered as pending only", () => {
    const h6 = CLAIMS.find((c) => c.id === "asing-borong")!;
    expect(h6.target).toEqual({ type: "finding", beliefs: [], pendingIds: ["H6"] });
  });

  it("every variant compiles and none matches the empty string", () => {
    for (const c of CLAIMS) for (const v of c.variants) expect(new RegExp(v, "i").test("")).toBe(false);
  });

  it("each kind is present", () => {
    for (const kind of ["belief", "situation", "promotion"] as const) expect(CLAIMS.some((c) => c.kind === kind)).toBe(true);
  });
});
