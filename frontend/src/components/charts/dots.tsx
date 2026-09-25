import type { ReactNode } from "react";

/**
 * 100-dot icon array ("X dari 100"): natural frequencies for a single
 * part-of-whole figure, per docs/PRODUCT.md §8 rule 1. Accessible name
 * spells the figure out; the dots themselves are decoration.
 */
export function IconDots({ filled, total = 100, cols = 10, size = 170, label }: { filled: number; total?: number; cols?: number; size?: number; label: string }) {
  const gap = size / cols;
  const rows = Math.ceil(total / cols);
  const dots = Array.from({ length: total }, (_, i) => (
    <circle key={i} cx={gap * (i % cols) + gap / 2} cy={gap * Math.floor(i / cols) + gap / 2} r={gap * 0.36} fill={i < filled ? "var(--viz-chart-blue)" : "#3a4358"} />
  ));
  return (
    <svg viewBox={`0 0 ${size} ${gap * rows}`} width={size} height={gap * rows} role="img" aria-label={label} className="max-w-full shrink-0">
      {dots}
    </svg>
  );
}

export function Key({ color, children }: { color: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 text-[13.5px] text-foreground">
      <span className="size-3 shrink-0 rounded-full" style={{ background: color }} />
      <span>{children}</span>
    </span>
  );
}
