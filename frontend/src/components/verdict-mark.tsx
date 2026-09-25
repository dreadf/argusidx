import type { Verdict } from "@/lib/findings-data";

const LABEL: Record<Verdict, string> = { yes: "Terbukti", no: "Tidak terbukti", mixed_or_inconclusive: "Tidak konsisten" };

/** Verdict icon (check / cross / wave) as inline SVG. Always paired with text for screen readers: never colour alone. */
export function VerdictMark({ verdict, size = 20 }: { verdict: Verdict; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", strokeWidth: 2.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, role: "img", "aria-label": LABEL[verdict] };
  if (verdict === "yes")
    return (
      <svg {...common} stroke="var(--viz-status-good)">
        <path d="M4 13l4 5L20 6" />
      </svg>
    );
  if (verdict === "no")
    return (
      <svg {...common} stroke="var(--viz-diverging-neg)">
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    );
  return (
    <svg {...common} stroke="var(--viz-status-warning)">
      <path d="M4 14c3-6 5-6 8 0s5 6 8 0" />
    </svg>
  );
}
