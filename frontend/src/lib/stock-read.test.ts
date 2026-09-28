import { beforeAll, describe, expect, it } from "vitest";
import { containsAdviceLanguage } from "@/lib/ask/advice-language-guard";
import { getFindingsData } from "@/lib/findings-data";
import { getAllStockCodes, getStockData } from "@/lib/stock-data";
import { getReadInput } from "@/lib/stock-read-data";
import {
  FINDING_BELIEF,
  SIGNAL_VERDICT,
  agenda,
  answers,
  dividendShape,
  earningsShape,
  popularSignals,
  quantifier,
  ringkasan,
  tanyaSuggestions,
  watchItems,
  type ReadInput,
  type SignalKey,
} from "@/lib/stock-read";

const T = 1e12;

describe("earningsShape", () => {
  it("reads loss years by direction", () => {
    expect(earningsShape([null, -2 * T, -90 * T, -5 * T, -1 * T])).toBe("loss_shrinking");
    expect(earningsShape([null, -1, -1, -2 * T, -5 * T])).toBe("loss_growing");
    expect(earningsShape([1, 1, 1, 2 * T, -1 * T])).toBe("turned_loss");
    expect(earningsShape([1, 1, 1, -2 * T, 1 * T])).toBe("back_to_profit");
  });
  it("needs three rising years for 'naik setiap tahun'", () => {
    expect(earningsShape([10, 20, 30, 40, 50])).toBe("rising_every_year");
    expect(earningsShape([50, 10, 30, 40, 50])).toBe("rising_every_year");
    expect(earningsShape([50, 10, 40, 30, 50])).toBe("up");
  });
  it("tells stable near the five-year high from plain stable", () => {
    expect(earningsShape([20, 29, 34, 34, 32.8])).toBe("stable_near_high");
    expect(earningsShape([100, 29, 34, 34, 32.8])).toBe("stable");
    expect(earningsShape([50, 40, 30, 20, 10])).toBe("falling_two_years");
    expect(earningsShape([1, 2, 3, 4, null])).toBe("none");
  });
});

describe("dividendShape", () => {
  it("classifies payment histories", () => {
    expect(dividendShape([null, null, null, null, null])).toBe("never");
    expect(dividendShape([132, 282, 650, 519, 406])).toBe("every_year_falling");
    expect(dividendShape([457, 155, 212, 277, 305])).toBe("every_year_rising");
    expect(dividendShape([null, null, null, null, 5.65])).toBe("first_time");
    expect(dividendShape([null, 61, 42, null, 64])).toBe("not_every_year");
    expect(dividendShape([10, 10, 10, 10, null])).toBe("skipped_latest");
  });
});

describe("quantifier", () => {
  it("maps a share of 100 to words", () => {
    expect(quantifier(12)).toBe("sedikit");
    expect(quantifier(26)).toBe("kurang dari separuh");
    expect(quantifier(50)).toBe("sekitar separuh");
    expect(quantifier(57)).toBe("lebih dari separuh");
    expect(quantifier(88)).toBe("sebagian besar");
  });
});

describe("findings", () => {
  it("every key names a finding, and each signal's copy matches that finding's verdict", async () => {
    const { scoreboard } = await getFindingsData();
    for (const belief of Object.values(FINDING_BELIEF)) expect(scoreboard.some((r) => r.belief === belief), belief).toBe(true);
    for (const [key, verdict] of Object.entries(SIGNAL_VERDICT)) {
      expect(scoreboard.find((r) => r.belief === FINDING_BELIEF[key as SignalKey])?.verdict, key).toBe(verdict);
    }
  });
});

/** The approved boards (Baru4-Saham-*), checked against the real data. */
describe("reference stocks", () => {
  const inputs: Record<string, ReadInput> = {};
  beforeAll(async () => {
    for (const code of ["ASII", "BBCA", "GOTO", "EMAS", "JARR", "TINS"]) inputs[code] = (await getReadInput(code, (await getStockData(code))!))!;
  });

  it("ASII: rows, signals and the one situation", () => {
    const r = inputs.ASII;
    const w = watchItems(r);
    const ring = ringkasan(r, w);
    expect(ring.rows.map((x) => x.state)).toEqual(["Turun, lebih ringan dari IHSG", "Stabil, dekat tertinggi lima tahun", "P/E di bawah sektornya", "Rutin, tapi turun dua tahun", "Lama di bawah puncak"]);
    expect(ring.rows[0].explain).toBe("-10,9% dalam setahun, IHSG -15,6%. 48 dari 65 saham industri bergerak lebih baik.");
    const sig = popularSignals(r, w);
    expect(sig.map((s) => s.key)).toEqual(["low_pe", "high_yield", "high_roe", "insider_buy", "news_tone"]);
    expect(sig[0].here).toContain("lebih rendah dari 84 dari 100 saham berlaba");
    expect(sig[1].here).toBe("Imbal dividen 7,9%, lebih tinggi dari 94 dari 100 saham.");
    expect(w.map((x) => x.kind)).toEqual(["long_below_peak"]);
    expect(w[0].here).toMatch(/^Rp 4\.910 sekarang, 35% di bawah puncak Rp 7\.575 \(28 Apr 2022\)/);
    expect(w[0].others?.figure).toBe("12 dari 100");
  });

  it("GOTO: a loss maker has no meaningful P/E and no dividend", () => {
    const r = inputs.GOTO;
    const ring = ringkasan(r, watchItems(r));
    expect(ring.lead.startsWith("GOTO masih rugi, tapi ruginya menyusut dua tahun berturut-turut.")).toBe(true);
    expect(ring.rows.map((x) => x.state)).toEqual(["Di harga terendah setahun", "Rugi, tapi menyusut", "P/E tidak bermakna", "Tidak membagikan", "Lama di bawah puncak, Perusahaan rugi"]);
    expect(answers(r, watchItems(r)).murah.lead).toBe("GOTO tidak punya P/E yang bermakna: rugi pada 2025.");
  });

  it("JARR: four situations, and a 0,2% yield is not called high", () => {
    const r = inputs.JARR;
    const w = watchItems(r);
    expect(w.map((x) => x.kind)).toEqual(["fall", "recent_price_suspension", "repeat_suspension", "recent_spike"]);
    expect(popularSignals(r, w).some((s) => s.key === "high_yield")).toBe(false);
    expect(answers(r, w).naik.lead).toBe("JARR naik 53% dalam 20 hari bursa sampai 20 Agu 2026. Lalu perdagangannya dihentikan sementara oleh bursa.");
  });

  it("EMAS: a new listing gets no one-year change", () => {
    const r = inputs.EMAS;
    const ring = ringkasan(r, watchItems(r));
    expect(ring.rows[0].state).toBe("Belum setahun di bursa");
    expect(watchItems(r).find((x) => x.kind === "recent_ipo")?.others).toBeNull();
  });

  it("TINS: nothing to note", () => {
    const r = inputs.TINS;
    expect(watchItems(r)).toEqual([]);
    expect(ringkasan(r, []).rows[4]).toEqual({ label: "Perlu diperhatikan", state: "Tidak ada", explain: "Tidak ada keadaan khusus yang sedang terjadi di TINS." });
  });

  it("BBCA: the yield flag and a falling price", () => {
    const r = inputs.BBCA;
    const w = watchItems(r);
    expect(w.map((x) => x.kind)).toEqual(["fall", "yield_far_above_average"]);
    expect(w[1].others).toEqual({ figure: "55 dari 100", rest: "perusahaan dengan tanda ini memangkas dividen tahun berikutnya (47 kasus, 2024)." });
    expect(tanyaSuggestions(r)[0]).toBe("Kenapa BBCA turun padahal labanya naik?");
    expect(ringkasan(r, w).lead).not.toMatch(/\d+ hal/);
    expect(agenda(r)[0]).toEqual({ date: "2026-09-16", label: "Pembayaran dividen Rp 25", past: true });
  });
});

describe("review fixes", () => {
  it("a flagged payout shows the flag's ratio, never under 100%", async () => {
    const r = (await getReadInput("FISH", (await getStockData("FISH"))!))!;
    const w = watchItems(r).find((x) => x.kind === "payout_above_earnings")!;
    expect(w.here).toBe("Membagikan 448% dari labanya sebagai dividen.");
    expect(answers(r, watchItems(r)).dividen.body).not.toMatch(/membagikan (\d|[1-9]\d)% dari labanya/);
  });
  it("a missing P/E with a 2025 profit is not called a loss", async () => {
    const r = (await getReadInput("PACK", (await getStockData("PACK"))!))!;
    const row = ringkasan(r, watchItems(r)).rows[2];
    expect(row.state).toBe("P/E tidak tersedia");
    expect(answers(r, watchItems(r)).murah.lead).toBe("P/E PACK tidak tercatat di data kami.");
  });
});

/** Every sentence the rules can produce, for every stock: no advice words, no em dash, no NaN or "undefined". The stock's own code is masked first: a ticker such as BELI is a name, not advice. */
describe("every stock", () => {
  it("produces clean copy", async () => {
    const codes = await getAllStockCodes();
    const bad: string[] = [];
    const walk = (code: string, v: unknown): void => {
      if (typeof v === "string") {
        if (containsAdviceLanguage(v.replaceAll(code, "KODE")) || v.includes("\u2014") || /NaN|undefined|Infinity|null/.test(v)) bad.push(`${code}: ${v}`);
      } else if (Array.isArray(v)) v.forEach((x) => walk(code, x));
      else if (v && typeof v === "object") Object.values(v).forEach((x) => walk(code, x));
    };
    for (const code of codes) {
      const r = await getReadInput(code, (await getStockData(code))!);
      if (!r) continue;
      const w = watchItems(r);
      walk(code, { ring: ringkasan(r, w), sig: popularSignals(r, w), w, a: answers(r, w), t: tanyaSuggestions(r), g: agenda(r) });
    }
    expect(bad.slice(0, 10)).toEqual([]);
  }, 120_000);
});
