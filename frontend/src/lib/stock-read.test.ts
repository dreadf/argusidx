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
  kesimpulan,
  rarestItem,
  tanyaSuggestions,
  watchItems,
  type ReadInput,
  type SignalKey,
  type WatchItem,
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
    for (const code of ["ASII", "BBCA", "GOTO", "RANS", "JARR", "TINS", "FILM"]) inputs[code] = (await getReadInput(code, (await getStockData(code))!))!;
  });

  it("ASII: headline, rows, signals and the one situation", () => {
    const r = inputs.ASII;
    const w = watchItems(r);
    const k = kesimpulan(r, w);
    expect(k.headline).toBe("Harga ASII turun 10,9% dalam setahun, lebih ringan dari IHSG (-15,6%), tapi turun lebih dalam dari kebanyakan saham industri.");
    expect(k.caption).toContain("48 dari 65 saham industri bergerak lebih baik.");
    expect(k.rows.map((x) => x.state)).toEqual(["Stabil, dekat tertinggi lima tahun", "P/E di bawah sektornya", "Rutin, tapi turun dua tahun"]);
    expect(k.watch).toEqual(["Lama di bawah puncak"]);
    expect(k.rarest).toBe("Keadaan ini sedang dialami 541 dari 962 saham.");
    const sig = popularSignals(r, w);
    expect(sig.map((s) => s.key)).toEqual(["low_pe", "high_yield", "high_roe", "insider_buy", "news_tone"]);
    expect(sig[0].here).toContain("lebih rendah dari 83% saham berlaba");
    expect(sig[1].here).toBe("Imbal dividen 8,2%, lebih tinggi dari 94% saham.");
    expect(sig.find((s) => s.key === "insider_buy")?.meaning).toBeNull();
    expect(w.map((x) => x.kind)).toEqual(["long_below_peak"]);
    expect(w[0].here).toBe("Jatuh 30% dari puncak Rp 7.575 pada 11 Jan 2023 dan belum kembali ke sana. Sekarang Rp 4.780, 37% di bawahnya.");
    expect(w[0].rate?.figure).toBe("12");
  });

  it("FILM: one fall, not two; a loss is never shown as a profit or a huge percent", () => {
    const r = inputs.FILM;
    const w = watchItems(r);
    expect(w.map((x) => x.kind)).toEqual(["loss_year", "fall", "earnings_two_year_decline"]);
    expect(w.find((x) => x.kind === "earnings_two_year_decline")?.here).toBe("Laba Rp 97 M pada 2023, laba Rp 5,6 M pada 2024, lalu rugi Rp 257 M pada 2025.");
    const k = kesimpulan(r, w);
    expect(k.headline).toBe("Harga FILM turun 75,3% dalam setahun, lebih dalam dari IHSG (-15,6%) dan dari hampir semua saham konsumer siklikal.");
    expect(k.figures.map((f) => [f.label, Math.round(f.stock * 1000) / 10, Math.round(f.ihsg * 1000) / 10])).toEqual([
      ["Setahun", -75.3, -15.6],
      ["Sejak puncak IHSG, 20 Jan 2026", -93.5, -27.3],
    ]);
    expect(rarestItem(r, w)?.kind).toBe("earnings_two_year_decline");
    expect(k.rarest).toBe("Paling jarang: laba turun dua tahun, keadaan yang sedang dialami 139 dari 962 saham.");
    const a = answers(r, w);
    expect(a.turun.body).toContain("FILM berbalik rugi Rp 257 M pada 2025.");
    expect(a.dividen.body).not.toContain("Tidak ada dividen untuk 2025");
  });

  it("GOTO: a loss maker has no meaningful P/E and no dividend", () => {
    const r = inputs.GOTO;
    const k = kesimpulan(r, watchItems(r));
    expect(k.rows.map((x) => x.state)).toEqual(["Rugi, tapi menyusut", "P/E tidak bermakna", "Tidak membagikan"]);
    expect(k.watch).toEqual(["Perusahaan rugi", "Lama di bawah puncak"]);
    expect(answers(r, watchItems(r)).murah.lead).toBe("GOTO tidak punya P/E yang bermakna: rugi pada 2025.");
  });

  it("JARR: four situations, and a 0,2% yield is not called high", () => {
    const r = inputs.JARR;
    const w = watchItems(r);
    expect(w.map((x) => x.kind)).toEqual(["recent_spike", "fall", "recent_price_suspension", "repeat_suspension"]);
    expect(popularSignals(r, w).some((s) => s.key === "high_yield")).toBe(false);
    expect(answers(r, w).naik.lead).toBe("JARR naik 53% dalam 20 hari bursa sampai 20 Agu 2026. Lalu perdagangannya dihentikan sementara oleh bursa.");
  });

  it("RANS: a new listing gets no one-year change", () => {
    const r = inputs.RANS;
    const k = kesimpulan(r, watchItems(r));
    expect(k.headline).toMatch(/^RANS baru melantai .*, jadi perubahan harganya setahun belum bisa dihitung\.$/);
    expect(k.caption).toBeNull();
    const ipo = watchItems(r).find((x) => x.kind === "recent_ipo")!;
    expect(ipo.rate).toBeNull();
    expect(ipo.note).toMatch(/tidak masuk uji IPO kami/);
  });

  it("TINS: nothing to note", () => {
    const r = inputs.TINS;
    expect(watchItems(r)).toEqual([]);
    const k = kesimpulan(r, []);
    expect(k.watch).toEqual([]);
    expect(k.rarest).toBeNull();
  });

  it("BBCA: the yield flag and a falling price", () => {
    const r = inputs.BBCA;
    const w = watchItems(r);
    expect(w.map((x) => x.kind)).toEqual(["fall", "yield_far_above_average"]);
    expect(w[1].rate).toEqual({ lead: "Dari 100 perusahaan dengan tanda ini (47 kasus, 2024),", figure: "55", rest: "memangkas dividen tahun berikutnya." });
    expect(kesimpulan(r, w).headline).toBe("Harga BBCA turun 16,2% dalam setahun, sejalan dengan IHSG (-15,6%), dan turun lebih dalam dari kebanyakan saham keuangan.");
    expect(tanyaSuggestions(r)[0]).toBe("Kenapa BBCA turun padahal labanya naik?");
    expect(answers(r, w).murah.check.some((c) => c.startsWith("P/E rendah"))).toBe(false);
    expect(agenda(r)[0]).toEqual({ date: "2026-03-26", label: "Laporan transaksi orang dalam terakhir", past: true });
  });
});

describe("rarestItem", () => {
  it("names the situation the fewest stocks are in, whatever its base rate rests on", () => {
    const item = (kind: WatchItem["kind"]) => ({ kind, title: kind, here: "", rate: null, note: null, href: "" });
    const r = { nowCounts: { fall: 270, near_ath_earnings_decline: 14 } } as unknown as ReadInput;
    expect(rarestItem(r, [item("fall"), item("near_ath_earnings_decline")])?.kind).toBe("near_ath_earnings_decline");
  });
});

describe("review fixes", () => {
  it("a flagged payout shows the flag's ratio, never under 100%", async () => {
    const r = (await getReadInput("FISH", (await getStockData("FISH"))!))!;
    const w = watchItems(r).find((x) => x.kind === "payout_above_earnings")!;
    expect(w.here).toBe("Membagikan 4,5 kali labanya sebagai dividen.");
    expect(answers(r, watchItems(r)).dividen.body).not.toMatch(/membagikan (\d|[1-9]\d)% dari labanya/);
  });
  it("a missing P/E with a 2025 profit is not called a loss", async () => {
    const r = (await getReadInput("PACK", (await getStockData("PACK"))!))!;
    const row = kesimpulan(r, watchItems(r)).rows[1];
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
        // A thousands-separated percent ("4.659%") only comes from dividing a loss by a profit.
        if (containsAdviceLanguage(v.replaceAll(code, "KODE")) || v.includes("\u2014") || /NaN|undefined|Infinity|null/.test(v) || /\d\.\d{3}(,\d+)?%/.test(v) || / dari \d+ dari 100/.test(v)) bad.push(`${code}: ${v}`);
      } else if (Array.isArray(v)) v.forEach((x) => walk(code, x));
      else if (v && typeof v === "object") Object.values(v).forEach((x) => walk(code, x));
    };
    for (const code of codes) {
      const r = await getReadInput(code, (await getStockData(code))!);
      if (!r) continue;
      const w = watchItems(r);
      // The one-year fall and the older fall are one fall at two ages, never both.
      if (w.some((x) => x.kind === "fall") && w.some((x) => x.kind === "long_below_peak")) bad.push(`${code}: fall and long_below_peak together`);
      walk(code, { k: kesimpulan(r, w), sig: popularSignals(r, w), w, a: answers(r, w), t: tanyaSuggestions(r), g: agenda(r) });
    }
    expect(bad.slice(0, 10)).toEqual([]);
  }, 120_000);
});
