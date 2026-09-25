/**
 * Histogram of "distance from the 52-week high" for the Peringkat chart.
 * Input: ratios <= 0 (e.g. -0.377). Ten bins of 10 percentage points each
 * (0 to -10, ..., -90 to -100); anything at or beyond -100% lands in the
 * last bin. `median` is returned as a 0..1 position along that axis.
 */
export function distanceBins(ratios: number[]): { bins: number[]; medianRatio: number; medianPos: number } {
  const bins = new Array(10).fill(0) as number[];
  for (const r of ratios) {
    const depth = Math.min(1, Math.max(0, -r));
    bins[Math.min(9, Math.floor(depth * 10))] += 1;
  }
  const sorted = [...ratios].sort((a, b) => a - b);
  const mid = sorted.length / 2;
  const medianRatio = sorted.length % 2 ? sorted[Math.floor(mid)] : (sorted[mid - 1] + sorted[mid]) / 2;
  return { bins, medianRatio, medianPos: Math.min(1, Math.max(0, -medianRatio)) };
}
