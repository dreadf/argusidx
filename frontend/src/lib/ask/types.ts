import type { Bucket } from "./classify";
import type { FindingRow } from "@/lib/findings-data";
import type { Quota } from "./quota";

export interface AskResponse {
  bucket: Bucket;
  /** Bare ticker (e.g. "BBCA") the answer is about, or null. Also carried into the next question so a follow-up like "jelaskan lebih mudah" still knows the stock. */
  stockCode: string | null;
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
  /** AI answers left for this user in the current 6 hours; null when no model is configured. */
  quota: Quota | null;
  /** Set when the AI allowance ran out and the answer came from data only. */
  limitReached: boolean;
}
