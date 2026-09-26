import { describe, expect, it } from "vitest";
import { outOfTen } from "@/lib/anomaly-data";

describe("outOfTen", () => {
  it("gives a range from two rates", () => {
    expect(outOfTen(0.61, 0.795)).toBe("6 sampai 8 dari 10");
  });
  it("collapses equal rounded values", () => {
    expect(outOfTen(0.71, 0.74)).toBe("7 dari 10");
  });
});
