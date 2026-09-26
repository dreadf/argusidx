import { describe, expect, it } from "vitest";
import { tiedAtTop } from "@/lib/derived-rankings-data";

describe("tiedAtTop", () => {
  it("counts rows sharing the first row's key", () => {
    expect(tiedAtTop([{ p: 100 }, { p: 100 }, { p: 99 }], (r) => r.p)).toBe(2);
  });
  it("is 0 for an empty list", () => {
    expect(tiedAtTop([], () => 1)).toBe(0);
  });
});
