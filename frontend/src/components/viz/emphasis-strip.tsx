/**
 * EmphasisStrip: the "emphasis" chart form (docs/PRODUCT.md §25): one
 * series is the point, the rest is context. Built to the dataviz skill's
 * mark specs (r>=4 markers, 2px surface ring, single accent hue for the
 * highlighted entity, gray for peers): same conventions as IconArray.
 *
 * Positions this company by RANK among its peer group (better_than_count
 * of comparable_count), not by raw metric value: the pipeline only ships
 * peer-group aggregate counts, not each individual peer's own value
 * (`pipeline/appdata/build_stock_pages.py`'s `build_peer_comparison`), so
 * a rank position is what's honestly available; it is not a claim about
 * exact spacing between peers, only about relative standing.
 */
"use client";

export interface EmphasisStripProps {
  /** How many peers this company beats (0-indexed rank from the bottom). */
  betterThanCount: number;
  /** Total peers compared against (excludes self). */
  comparableCount: number;
  lowLabel?: string;
  highLabel?: string;
  className?: string;
}

export function EmphasisStrip({
  betterThanCount,
  comparableCount,
  lowLabel = "Lebih rendah",
  highLabel = "Lebih tinggi",
  className,
}: EmphasisStripProps) {
  const total = comparableCount + 1; // peers + self
  const dotSize = 8;
  const gap = 10;
  const width = total * (dotSize + gap);
  const height = dotSize + 4;

  // Self's position among `total` slots, ordered low -> high by rank.
  const selfIndex = Math.min(betterThanCount, comparableCount);

  return (
    <div className={className}>
      <svg
        role="img"
        aria-label={`Lebih tinggi dari ${betterThanCount} dari ${comparableCount} perusahaan sejenis`}
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto" }}
      >
        {Array.from({ length: total }).map((_, i) => {
          const isSelf = i === selfIndex;
          return (
            <circle
              key={i}
              cx={i * (dotSize + gap) + dotSize / 2}
              cy={height / 2}
              r={isSelf ? (dotSize / 2) * 1.4 : dotSize / 2}
              fill={isSelf ? "var(--viz-cat-1)" : "var(--viz-baseline)"}
              stroke="var(--viz-surface)"
              strokeWidth={2}
            />
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-[var(--viz-ink-muted)]">
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  );
}
