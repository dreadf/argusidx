import type { FindingEvidence } from "@/lib/findings-data";

/**
 * Plain-Indonesian display copy for a finding's sample line. The data
 * (data/app/findings.json) carries research shorthand such as
 * "n=1.148 (holdout)"; users never see that. Board:
 * Temuan-Mobile-v2, list row: "1.148 saham, 2024-2026".
 */

const UNIT_BY_HYPOTHESIS: Record<string, string> = {
  H4: "perusahaan",
  H8: "kejadian",
  H11: "kejadian",
  H1: "saham",
  H5: "saham",
  H14: "saham",
};

/** "2024–2026" (en dash) -> "2024-2026"; first year range in the period text, else first single year. */
function yearsOf(period: string): string | null {
  const range = period.match(/(\d{4})\s*[–-]\s*(\d{4})/);
  if (range) return `${range[1]}-${range[2]}`;
  const single = period.match(/\d{4}/);
  return single ? single[0] : null;
}

function countOf(n: string, hypothesis: string): string | null {
  // H14: "n=26.701 titik data (holdout, 887 saham)": the number of stocks is the meaningful one.
  const stocks = n.match(/(\d[\d.]*)\s+saham\)/);
  if (stocks) return `${stocks[1]} saham`;
  if (/kombinasi diuji/.test(n)) return n.split(",")[0];
  const numbers = [...n.matchAll(/n=([\d.]+)(?:\s*[–-]\s*([\d.]+))?/g)];
  if (numbers.length === 0) return null;
  const pooled = /pooled/.test(n);
  const unit = pooled ? "pengamatan" : (UNIT_BY_HYPOTHESIS[hypothesis.split(",")[0].trim()] ?? "pengamatan");
  if (hypothesis === "H11") return `${numbers.map((m) => m[1]).join(" dan ")} ${unit}`;
  const first = numbers[0];
  return first[2] ? `${first[1]} sampai ${first[2]} ${unit}` : `${first[1]} ${unit}`;
}

/** One short line: "1.148 saham, 2024-2026". Falls back to the raw text only if nothing parses. */
export function sampleLine(evidence: FindingEvidence): string {
  const count = countOf(evidence.n, evidence.hypothesis_id);
  const years = yearsOf(evidence.period_id);
  if (count === null) return evidence.n.replace(/\(([^)]*)\)/g, "").replace(/\bn=/g, "").trim();
  return years ? `${count}, ${years}` : count;
}

/** True when the sample was re-tested on data kept apart from where the pattern was found (a "holdout"). */
export function isRetested(evidence: FindingEvidence): boolean {
  return /holdout/.test(evidence.n);
}

/** Longer plain sentence for detail pages: "Diuji ulang pada data yang terpisah: 1.148 saham, 2024-2026." */
export function sampleSentence(evidence: FindingEvidence): string {
  const line = sampleLine(evidence);
  return isRetested(evidence) ? `Diuji ulang pada data terpisah: ${line}.` : `${line}.`;
}
