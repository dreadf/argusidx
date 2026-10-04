import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { findingSlug, type FindingRow } from "@/lib/findings-data";
import { ogPath, parseShareParams, resolveShare, sharePath, shareTargetOf, shareTitle } from "./share";
import { readTip } from "./tip-reader";
import { loadRealStocks } from "./tip-test-deps";
import { buildTipView, findUnknownCodes, tipDeps, type TipBundle } from "./tip-view";

const findings = (
  JSON.parse(readFileSync(path.join(__dirname, "..", "..", "..", "..", "data", "app", "findings.json"), "utf-8")) as { scoreboard: FindingRow[] }
).scoreboard;

const bundle: TipBundle = {
  stocks: loadRealStocks().map((s) => ({ code: s.code, name: s.companyName, short: s.companyName, price: "Rp 1", change: "-1,0%", negative: true, situations: [] })),
  findings: findings.map((f) => ({ belief: f.belief, hypothesisId: f.evidence.hypothesis_id, slug: findingSlug(f), verdict: f.verdict, title: f.title_short_id, line: f.result_short_id })),
  situationClaims: { fall: { slug: "turun-banyak", line: "Contoh." } },
};

function view(text: string) {
  const reading = readTip(text, tipDeps(bundle));
  return buildTipView(text, reading, bundle, findUnknownCodes(text, new Set(bundle.stocks.map((s) => s.code))));
}

describe("share link", () => {
  it("builds a link from a result and rebuilds the same rows from it", () => {
    const v = view("BBCA oversold banget, pasti mantul");
    const target = shareTargetOf(v)!;
    expect(target.codes).toEqual(["BBCA"]);
    expect(target.keys.length).toBeGreaterThan(0);

    const url = new URL(sharePath(target), "https://example.test");
    const parsed = parseShareParams(url.pathname.split("/")[2], url.searchParams.get("k"))!;
    expect(parsed).toEqual(target);

    const back = resolveShare(bundle, parsed);
    expect(back.stocks.map((s) => s.code)).toEqual(["BBCA"]);
    expect(back.claims.map((c) => c.key)).toEqual(v.claims.filter((c) => c.share).map((c) => c.key));
    expect(shareTitle(back).startsWith("BBCA: ")).toBe(true);
  });

  it("never puts the message text in the link or the preview address", () => {
    const text = "BBCA oversold banget, pasti mantul, hubungi 08123456789";
    const target = shareTargetOf(view(text))!;
    for (const s of [sharePath(target), ogPath(target)]) {
      expect(s).not.toMatch(/mantul|08123|hubungi|oversold banget/i);
    }
  });

  it("shares nothing when there is no stock or no tested claim", () => {
    expect(shareTargetOf(view("oversold banget, pasti mantul"))).toBeNull();
    expect(shareTargetOf(view("BBCA bagus"))).toBeNull();
  });

  it("drops malformed codes and keys instead of guessing", () => {
    expect(parseShareParams("bbca", "t~x,<script>,s~nope,s~fall")).toEqual({ codes: ["BBCA"], keys: ["t~x", "s~fall"] });
    expect(parseShareParams("../etc", undefined)).toBeNull();
    expect(parseShareParams("BBCA-BBRI-TLKM-ASII-GOTO", "")!.codes).toHaveLength(3);
  });

  it("skips ids that are not in the data", () => {
    const r = resolveShare(bundle, { codes: ["BBCA", "ZZZZ"], keys: ["t~tidak-ada", "s~fall"] });
    expect(r.stocks.map((s) => s.code)).toEqual(["BBCA"]);
    expect(r.claims.map((c) => c.title)).toEqual(["Harga turun banyak"]);
  });
});
