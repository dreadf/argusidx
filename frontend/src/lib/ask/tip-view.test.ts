import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { findingSlug, type FindingRow } from "@/lib/findings-data";
import { loadRealStocks } from "./tip-test-deps";
import { readTip } from "./tip-reader";
import { beliefSlug, buildTipView, findUnknownCodes, routeInput, suggestCodes, tipDeps, type TipBundle } from "./tip-view";

const findings = (
  JSON.parse(readFileSync(path.join(__dirname, "..", "..", "..", "..", "data", "app", "findings.json"), "utf-8")) as { scoreboard: FindingRow[] }
).scoreboard;

const bundle: TipBundle = {
  stocks: loadRealStocks().map((s) => ({ code: s.code, name: s.companyName, short: s.companyName, price: "Rp 1", change: "-1,0%", negative: true, situations: [] })),
  findings: findings.map((f) => ({ belief: f.belief, hypothesisId: f.evidence.hypothesis_id, slug: findingSlug(f), verdict: f.verdict, title: f.title_short_id, line: f.result_short_id })),
  situationClaims: { fall: { slug: "turun-banyak", line: "Contoh." } },
};
const codes = new Set(bundle.stocks.map((s) => s.code));

function run(text: string, confirmed: string[] = []) {
  const reading = readTip(text, tipDeps(bundle));
  const unknown = findUnknownCodes(text, codes);
  return { route: routeInput(text, reading, unknown), view: buildTipView(text, reading, bundle, unknown, confirmed), unknown };
}

describe("routeInput", () => {
  it("sends a pasted tip to the deterministic reader", () => {
    const { route } = run("BBCA oversold banget, pasti mantul! Asing borong, TP 12000 🚀 BUMI juga ikut, buruan sebelum terlambat");
    expect(route).toBe("tip");
  });

  it("sends questions without a testable claim to the question path", () => {
    expect(run("Jelaskan BBCA dengan bahasa sederhana").route).toBe("question");
    expect(run("Apa itu ROE?").route).toBe("question");
    expect(run("Berapa nilai pasar TLKM").route).toBe("question");
  });

  it("shows the deterministic result when a question also names a tested claim", () => {
    const { route, view } = run("Apakah saham murah (P/E rendah) lebih untung?");
    expect(route).toBe("tip");
    expect(view.claims.map((c) => c.title).join(" ")).toMatch(/murah/i);
  });

  it("keeps text over the question limit in the browser", () => {
    expect(run(`Jelaskan BBCA ${"dengan bahasa sederhana ".repeat(20)}`).route).toBe("tip");
  });
});

describe("buildTipView", () => {
  const board = "BBCA oversold banget, pasti mantul! Asing borong, TP 12000 🚀 BUMI juga ikut, buruan sebelum terlambat";

  it("reads the board example: one stock, a confirm chip, two claims, the untested wording", () => {
    const { view } = run(board);
    expect(view.stocks.map((s) => s.code)).toEqual(["BBCA"]);
    expect(view.ambiguous).toEqual([{ code: "BUMI", prompt: "Maksud Anda saham BUMI?" }]);
    expect(view.claims.map((c) => [c.verdict, c.href.startsWith("/temuan/")])).toEqual([
      ["no", true],
      ["no", true],
    ]);
    expect(view.untested).toEqual(["TP 12000"]);
    expect(view.notices).toEqual([]);
  });

  it("adds a confirmed common-word stock and drops its chip", () => {
    const { view } = run(board, ["BUMI"]);
    expect(view.stocks.map((s) => s.code)).toEqual(["BBCA", "BUMI"]);
    expect(view.ambiguous).toEqual([]);
  });

  it("gives each claim its own row, never merged", () => {
    const { view } = run("dividen gede, laba naik terus, berita positif");
    expect(view.claims.length).toBeGreaterThanOrEqual(3);
    expect(new Set(view.claims.map((c) => c.key)).size).toBe(view.claims.length);
  });

  it("links a situation claim to its page and skips the verdict chip", () => {
    const { view } = run("BBCA turun banyak minggu ini");
    expect(view.claims).toContainEqual(expect.objectContaining({ verdict: null, href: "/situasi/turun-banyak", line: "Contoh." }));
  });

  it("notes a message with no stock code", () => {
    const { view } = run("asing borong pasti naik");
    expect(view.notices).toEqual([{ kind: "no-code" }]);
  });

  it("names an unknown code and suggests near ones", () => {
    const { route, view, unknown } = run("$BBZA oversold banget");
    expect(unknown).toEqual(["BBZA"]);
    expect(route).toBe("tip");
    const n = view.notices[0];
    expect(n.kind).toBe("unknown-code");
    if (n.kind === "unknown-code") {
      expect(n.suggestions).toContain("BBCA");
      expect(n.total).toBe(bundle.stocks.length);
    }
  });

  it("flags a message over 2.000 characters", () => {
    const { view } = run(`BBCA oversold. ${"oversold ".repeat(300)}`);
    expect(view.notices.map((n) => n.kind)).toContain("too-long");
  });
});

describe("findUnknownCodes", () => {
  it("only reacts where the sender marked a code, never to plain capitalised words", () => {
    expect(findUnknownCodes("BELI SEKARANG JUAL NANTI GAN", codes)).toEqual([]);
    expect(findUnknownCodes("saham ZZZZ lagi naik", codes)).toEqual(["ZZZZ"]);
    expect(findUnknownCodes("ZZZZ TP 500", codes)).toEqual(["ZZZZ"]);
    expect(findUnknownCodes("zzzz.jk breakout", codes)).toEqual(["ZZZZ"]);
    expect(findUnknownCodes("$BBCA naik", codes)).toEqual([]);
  });
});

describe("suggestCodes", () => {
  it("returns at most three codes within two typos, closest first", () => {
    expect(suggestCodes("BBCX", ["BBRI", "BBCA", "TLKM", "BBNI"])[0]).toBe("BBCA");
    expect(suggestCodes("QQQQ", ["BBRI", "BBCA"])).toEqual([]);
    expect(suggestCodes("BBCX", ["BBCA", "BBCB", "BBCC", "BBCD"])).toHaveLength(3);
  });
});

describe("beliefSlug", () => {
  it("matches findingSlug for every published finding", () => {
    for (const f of findings) expect(beliefSlug(f.belief)).toBe(findingSlug(f));
  });
});
