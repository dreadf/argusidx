import { describe, expect, it } from "vitest";
import { parseLedgerTotal } from "@/lib/credit-ledger";

describe("parseLedgerTotal", () => {
  it("reads the running total of the last dated row", () => {
    const md = ["| Date | Endpoint | Purpose | Cost | Running total |", "|---|---|---|---|---|", "| 2026-09-07 | `/a` | x | 1 | 31 |", "| 2026-09-26 | `/b` | y | 126 | 734 |", "", "1. note"].join("\n");
    expect(parseLedgerTotal(md)).toBe(734);
  });
  it("returns null when there are no dated rows", () => {
    expect(parseLedgerTotal("nothing here")).toBeNull();
  });
});
