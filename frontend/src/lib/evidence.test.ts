import { describe, expect, it } from "vitest";
import { sampleLine } from "@/lib/finding-copy";
import { orderFindings, type FindingRow, type Verdict } from "@/lib/findings-data";
import { foreignFlowLine, ipoPriceLine } from "@/lib/stock-summary";

const row = (id: string, verdict: Verdict, extra: Partial<FindingRow["evidence"]> = {}): FindingRow => ({
  belief: id,
  verdict,
  label: "",
  belief_id: "",
  label_id: "",
  title_short_id: id,
  result_short_id: "",
  evidence: { hypothesis_id: id, n: "", period_id: "", limit_id: "", ...extra },
});

describe("sampleLine for the two newest findings", () => {
  it("H6 counts list appearances over a short month range", () => {
    const line = sampleLine({ hypothesis_id: "H6", n: "n=61 hari, 3.660 saham di daftar", period_id: "Daftar asing harian Januari 2025 sampai September 2026, hasil 5 hari bursa", limit_id: "" });
    expect(line).toBe("3.660 saham di daftar, Jan 2025 sampai Sep 2026");
  });

  it("H18 counts the events of both phases, not the holdout's", () => {
    const line = sampleLine({ hypothesis_id: "H18", n: "n=292 kejadian (uji akhir 2026)", period_id: "Pemberitahuan pembelian 2025 (data awal) dan 2026 (uji akhir), hasil 20 hari bursa", limit_id: "" });
    expect(line).toBe("660 kejadian, 2025 sampai 2026");
  });

  it("leaves the other findings as before", () => {
    const line = sampleLine({ hypothesis_id: "H5, H10", n: "n=1.148 (holdout)", period_id: "Formasi 2024–2026, hasil diukur Mei–Sep tahun berikutnya", limit_id: "" });
    expect(line).toBe("1.148 saham, 2024-2026");
  });

  it("falls back when the H6 text does not parse", () => {
    const line = sampleLine({ hypothesis_id: "H6", n: "n=61 hari", period_id: "2025", limit_id: "" });
    expect(line).not.toContain("saham di daftar");
  });
});

describe("orderFindings", () => {
  it("puts proven first, then not proven, then unclear, newest tests leading their group", () => {
    const rows = [row("H14", "no"), row("H11", "mixed_or_inconclusive"), row("H18", "no"), row("H4", "yes"), row("H17", "no"), row("H6", "no"), row("H10", "yes")];
    expect(orderFindings(rows).map((r) => r.evidence.hypothesis_id)).toEqual(["H4", "H10", "H6", "H18", "H17", "H14", "H11"]);
  });

  it("keeps the file order inside a group and does not change its input", () => {
    const rows = [row("H1", "no"), row("H2", "no"), row("H3", "no")];
    expect(orderFindings(rows).map((r) => r.evidence.hypothesis_id)).toEqual(["H1", "H2", "H3"]);
    expect(rows.map((r) => r.evidence.hypothesis_id)).toEqual(["H1", "H2", "H3"]);
  });
});

describe("optional stock rows", () => {
  it("words the foreign flow by the sign of the number, with its date", () => {
    expect(foreignFlowLine(-12.4e9, "2026-10-06")).toBe("Rp 12,4 M jual bersih, per 06/10/2026");
    expect(foreignFlowLine(3.2e9, "2026-10-06")).toBe("Rp 3,2 M beli bersih, per 06/10/2026");
  });

  it("puts the IPO offer price next to the last close", () => {
    expect(ipoPriceLine(100, 560)).toBe("Rp 100 ke Rp 560");
  });
});
