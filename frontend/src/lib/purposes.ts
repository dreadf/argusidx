import type { Verdict } from "@/lib/verdict-chip";

/** The "why are you looking" chips on the stock page and the shape of their answers. Client-safe. */
export type Purpose = "turun" | "murah" | "dividen" | "tip" | "naik";

export const PURPOSES: { key: Purpose; label: string }[] = [
  { key: "turun", label: "Harganya turun" },
  { key: "murah", label: "Kelihatan murah" },
  { key: "dividen", label: "Dividennya besar" },
  { key: "tip", label: "Ada yang merekomendasikan" },
  { key: "naik", label: "Harganya naik tinggi" },
];

export interface Evidence {
  text: string;
  /** Tested verdict; "base" for a past frequency; null for a plain fact. */
  kind: Verdict | "base" | null;
  href?: string;
}

export interface Answer {
  lead: string;
  body: string;
  evidence: Evidence[];
  check: string[];
  /** Tip: show the paste box. */
  paste?: boolean;
}
