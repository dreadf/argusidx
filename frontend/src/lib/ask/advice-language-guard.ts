/**
 * Runtime port of `scripts/check_no_advice_language.py`'s patterns, used
 * ONLY to gate LLM-generated prose before it's ever shown to a user.
 *
 * Why this exists as a second copy rather than one shared source: the
 * Python script runs at build/review time over source files on disk: an
 * `.tsx`/`.md` scan is a fine place for a Python subprocess. This one runs
 * per-request, inside a Node.js Route Handler, against text that doesn't
 * exist until an LLM call returns it: a different runtime, a different
 * job (defense-in-depth on live model output, not a source-code linter).
 * Keeping the pattern LIST itself identical between the two is what
 * matters; if the Python list changes, mirror the change here too.
 *
 * Template-written copy (everything else in this codebase) is still
 * checked by the real Python scanner as part of `CLAUDE.md`'s "before
 * saying something is done" gate: this module never substitutes for
 * that, it only covers the one case the Python scanner structurally
 * cannot: text that's generated at request time, after the build.
 */
const ADVICE_PATTERNS: RegExp[] = [
  // Indonesian: direct recommendation / imperative framing
  /\bsebaiknya\b/i,
  /\brekomendasi\b/i,
  /\bdirekomendasikan\b/i,
  /\bdisarankan\b/i,
  /\bmenyarankan\b/i,
  /\blayak (di)?beli\b/i,
  /\bharus (membeli|menjual|beli|jual|menahan)\b/i,
  /\bwaktu(nya)? (yang )?tepat (untuk )?(membeli|menjual|beli|jual|bertransaksi)\b/i,
  /\bsaatnya (membeli|menjual|beli|jual)\b/i,
  /\b(beli|jual) sekarang\b/i,
  /\bpatut (dibeli|dijual|dimiliki)\b/i,
  /\bhindari saham\b/i,
  /\blebih baik (membeli|menjual|beli|jual|menahan)\b/i,
  // The four alarm-style words below (a market-pressure state pill, an
  // avoidance directive, a danger word, and a caution phrase) must never
  // reach the product as an imperative; the Pasar/Kesimpulan state labels
  // use "tertekan" and "risiko aktif" instead. Added 2026-09-27, bare-word
  // and deliberately broad, mirroring the Python scanner. This comment
  // deliberately doesn't spell the words out, so it doesn't trip its own
  // scanner; OJK's programme name built on the first word is masked out
  // before matching, see below.
  /\bwaspada\b/i,
  /\bhindari\b/i,
  /\bbahaya\b/i,
  /\bhati[- ]?hati\b/i,
  // English: direct recommendation / imperative framing
  /\byou should (buy|sell|hold)\b/i,
  /\bwe recommend\b/i,
  /\brecommended (buy|sell|hold)\b/i,
  /\ba good (buy|time to buy|time to sell)\b/i,
  /\bworth buying\b/i,
  /\b(buy|sell) now\b/i,
  /\bstrong buy\b/i,
  /\bbetter to (buy|sell|hold)\b/i,
];

/** Legitimate uses of an otherwise-flagged word, masked out before matching
 * so any other, unrelated advice pattern in the same text still gets
 * caught. Kept identical in spirit to `check_no_advice_language.py`'s
 * `ALLOWLIST_PHRASES`, though this guard runs on live model output rather
 * than source files, so there is no line/file to report. */
const ALLOWLIST_PHRASES: RegExp[] = [/waspada investasi/gi];

/** True if `text` matches any advice-shaped pattern. Deliberately broad:
 * same philosophy as the Python scanner: a false positive here just falls
 * back to template prose (cheap), a missed real recommendation reaching a
 * user is not. */
export function containsAdviceLanguage(text: string): boolean {
  const masked = ALLOWLIST_PHRASES.reduce((acc, phrase) => acc.replace(phrase, ""), text);
  return ADVICE_PATTERNS.some((pattern) => pattern.test(masked));
}
