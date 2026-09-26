import type { Bucket } from "./classify";
import type { FindingRow } from "@/lib/findings-data";
import type { Quota } from "./quota";
import type { StockCard } from "./stock-card";

export interface AskResponse {
  bucket: Bucket;
  /** Bare ticker (e.g. "BBCA") the answer is about, or null. Also carried into the next question so a follow-up like "jelaskan lebih mudah" still knows the stock. */
  stockCode: string | null;
  /** Head line and key facts of that stock, for the result card; null when the answer is not about one stock. */
  card: StockCard | null;
  /** Set when the user asked for an AI answer but got one from data: "limit" = allowance used up, "unavailable" = model off or failed. Null otherwise, including when the user chose data only. */
  notice: "limit" | "unavailable" | null;
  /** Plain-Bahasa answer: written by the model when it is on, within its limit and passes every check, otherwise a template. Every figure in it also appears in `facts` or `findings`. */
  prose: string;
  /** The exact fact sentences the answer rests on, always shown as a list so the answer never depends on trusting the prose alone. */
  facts: string[];
  /** Tested findings the answer touches, each with its own verdict, never merged. */
  findings: FindingRow[];
  /** Pages behind the facts. */
  links: { label: string; href: string }[];
  /** Which path actually produced `prose`. */
  source: "template" | "gemini";
  /** AI answers left for this user in the current 24 hours; null when no model is configured. */
  quota: Quota | null;
  /** Set when the AI allowance ran out and the answer came from data only. */
  limitReached: boolean;
}
