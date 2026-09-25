import { matchFindingTopics } from "./finding-topics";

/**
 * The routing buckets from docs/PRODUCT.md §7, plus one internal 6th
 * state ("ambiguous") the plan names separately from `no_data`:
 * `no_data` means "a real, intelligible question about something we
 * genuinely don't have" — `ambiguous` means the classifier can't tell
 * what's even being asked. Conflating the two would give a confused
 * question ("asu") the same "here's what's known instead" treatment
 * meant for a real, answerless question, which isn't honest either way.
 */
export type Bucket = "finding" | "untested_data" | "answered" | "no_data" | "unanswerable" | "advice_seeking" | "ambiguous";

export interface Classification {
  bucket: Bucket;
  /** `belief` keys from findings.json this question's wording matched — only
   * populated when bucket is "finding"; may be more than one, never merged. */
  matchedBeliefs: string[];
}

// Question-shaped patterns — these look at what the USER is asking, which is
// a different job from advice-language-guard.ts (which looks at what an LLM
// wrote back). A question can ask for advice using words that, phrased as a
// statement, wouldn't trip the output guard at all ("mending beli yang mana"
// has no imperative verb aimed at the reader the way "sebaiknya membeli"
// does) — so this list is deliberately its own, not reused from there.
const ADVICE_SEEKING_PATTERNS: RegExp[] = [
  /\b(apakah )?(saya )?(harus|sebaiknya|perlu) (beli|jual|membeli|menjual|menahan)\b/i,
  /\bharus (beli|jual)\b/i,
  /\brekomendasi\b/i,
  /\blayak (di)?beli\b/i,
  /\bsaham (apa|mana) yang (bagus|baik|cocok|layak)\b/i,
  /\bsaham terbaik\b/i,
  /\bmending (beli|jual|pilih)\b/i,
  /\bworth (it )?(to )?buy(ing)?\b/i,
  /\bshould i (buy|sell|hold)\b/i,
  /\bwhat should i buy\b/i,
  /\brecommend\b/i,
];

const UNANSWERABLE_PATTERNS: RegExp[] = [
  /\b(akan|bakal) (naik|turun|melejit|anjlok)\b/i,
  /\b(naik|turun) (besok|minggu depan|bulan depan|tahun depan)\b/i,
  /\bprediksi\b/i,
  /\bramalan\b/i,
  /\btarget harga\b/i,
  /\bwill (it |the price )?(rise|fall|go up|go down|recover)\b/i,
  /\bpredict\b/i,
  /\bprice target\b/i,
];

function looksAmbiguous(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 4) return true;
  if (!/[a-zA-Z]/.test(trimmed)) return true;
  const GREETINGS = ["hi", "halo", "hai", "tes", "test", "hello", "help", "bantuan"];
  return GREETINGS.includes(trimmed.toLowerCase());
}

/**
 * Deterministic classification — the guaranteed-available path (docs/
 * PRODUCT.md §0 rule 4: "the app must work fully with the LLM switched
 * off"). `hasRecognizedStock` comes from stock-lookup.ts, computed by the
 * caller so this function stays a pure, easily-reasoned-about string
 * match with no I/O of its own.
 *
 * Precedence matters and is deliberate: advice-seeking is checked first
 * because a question can be BOTH advice-seeking and about a real stock
 * ("apakah saya harus jual BBCA sekarang?") — the advice framing must win,
 * never get quietly absorbed into a data lookup. Unanswerable is checked
 * next for the same reason relative to a finding/data match.
 */
export function classify(question: string, hasRecognizedStock: boolean): Classification {
  if (ADVICE_SEEKING_PATTERNS.some((p) => p.test(question))) {
    return { bucket: "advice_seeking", matchedBeliefs: [] };
  }
  if (UNANSWERABLE_PATTERNS.some((p) => p.test(question))) {
    return { bucket: "unanswerable", matchedBeliefs: [] };
  }
  const matchedBeliefs = matchFindingTopics(question);
  if (matchedBeliefs.length > 0) {
    return { bucket: "finding", matchedBeliefs };
  }
  if (hasRecognizedStock) {
    return { bucket: "untested_data", matchedBeliefs: [] };
  }
  if (looksAmbiguous(question)) {
    return { bucket: "ambiguous", matchedBeliefs: [] };
  }
  return { bucket: "no_data", matchedBeliefs: [] };
}
