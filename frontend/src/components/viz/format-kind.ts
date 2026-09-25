/**
 * Shared value-format kinds for the chart primitives (count-columns,
 * grouped-columns). A plain string, not a function: these charts are
 * used from server components, and a function prop can't cross the
 * server/client component boundary (Next.js RSC serialization rule).
 */
export type FormatKind = "count" | "percent" | "percent-signed";

export function resolveFormat(kind: FormatKind): (value: number) => string {
  if (kind === "percent") return (v: number) => `${v}%`;
  if (kind === "percent-signed") return (v: number) => `${v > 0 ? "+" : ""}${v}%`;
  return (v: number) => v.toLocaleString("id-ID");
}
