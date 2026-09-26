import type { Verdict } from "@/lib/findings-data";
import type { SituationLine } from "./stock-card";
import type { SituationId } from "./tip-claims";
import type { TipDeps, TipReading } from "./tip-reader";

/**
 * View-model for the Tanya page: decides whether what the user typed is a
 * pasted message or a question, and turns a tip reading into the rows the
 * result shows. Pure and browser-safe (types only from server modules): a
 * pasted message is read in the browser and its text never leaves it.
 */

/** The question path (/api/ask) accepts at most this many characters. */
export const MAX_QUESTION_CHARS = 300;

/** What the browser needs to read a message: every stock, the tested findings, the situation lines. Built by tip-bundle.ts, served by /api/ask/tip-data (no user text involved). */
export interface TipBundleStock {
  code: string;
  /** Registered name, "PT Bank Central Asia Tbk." */
  name: string;
  /** Display name, "Bank Central Asia". */
  short: string;
  price: string | null;
  change: string | null;
  negative: boolean;
  situations: SituationLine[];
}

export interface TipBundleFinding {
  belief: string;
  hypothesisId: string;
  slug: string;
  verdict: Verdict;
  title: string;
  /** One short line: the result of the test. */
  line: string;
}

export interface TipBundle {
  /** Ordered by market value, largest first. */
  stocks: TipBundleStock[];
  findings: TipBundleFinding[];
  situationClaims: Partial<Record<SituationId, { slug: string; line: string }>>;
}

const depsCache = new WeakMap<TipBundle, TipDeps>();

/** The reader's inputs for a bundle. Cached: readTip indexes the stock list by array identity, so the same array must be passed each time. */
export function tipDeps(bundle: TipBundle): TipDeps {
  let deps = depsCache.get(bundle);
  if (!deps) {
    deps = {
      stocks: bundle.stocks.map((s) => ({ code: s.code, companyName: s.name })),
      findings: bundle.findings.map((f) => ({ belief: f.belief, evidence: { hypothesis_id: f.hypothesisId } })),
    };
    depsCache.set(bundle, deps);
  }
  return deps;
}

/** URL slug of a finding's page (same rule as findingSlug in findings-data.ts, which reads files and so cannot be imported in the browser). */
export function beliefSlug(belief: string): string {
  return belief
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

// ---------------------------------------------------------------- routing

export type InputRoute = "tip" | "question";

const UNKNOWN_CODE_RES: RegExp[] = [
  /[$#]([A-Za-z]{4})(?![A-Za-z0-9])/g,
  /(?<![A-Za-z0-9])([A-Za-z]{4})\.jk(?![A-Za-z])/gi,
  /\b(?:saham|emiten|kode|ticker|tiker)\s*[:-]?\s*([A-Z]{4})(?![A-Za-z0-9])/g,
  /(?<![A-Za-z0-9])([A-Z]{4})\s+(?:TP\d*|tp\d*|target|entry|SL|sl)\b/g,
];

/** Ticker-shaped mentions that are not a listed stock: only where the sender marked it as a code ($, #, .JK, "saham", or next to a target). Never plain words. */
export function findUnknownCodes(text: string, knownCodes: ReadonlySet<string>): string[] {
  const found: string[] = [];
  const head = text.slice(0, 2000);
  for (const re of UNKNOWN_CODE_RES) {
    for (const m of head.matchAll(re)) {
      const code = m[1].toUpperCase();
      if (!knownCodes.has(code) && !found.includes(code)) found.push(code);
    }
  }
  return found.slice(0, 3);
}

function editDistance(a: string, b: string): number {
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let diag = prev[0];
    prev[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const up = prev[j];
      prev[j] = Math.min(prev[j] + 1, prev[j - 1] + 1, diag + (a[i - 1] === b[j - 1] ? 0 : 1));
      diag = up;
    }
  }
  return prev[b.length];
}

/** Up to three listed codes within two typos of `code`, closest first, larger companies first among equals. `codes` must be ordered by market value. */
export function suggestCodes(code: string, codes: readonly string[]): string[] {
  return codes
    .map((c, order) => ({ c, order, d: editDistance(code, c) }))
    .filter((x) => x.d <= 2)
    .sort((a, b) => a.d - b.d || a.order - b.order)
    .slice(0, 3)
    .map((x) => x.c);
}

/**
 * A message goes to the deterministic tip reader when the reader recognises
 * something to test in it: a claim it has a finding or situation for, wording
 * typical of promotional messages, or a code that is not listed. Anything
 * over the question limit also stays in the browser. Otherwise it is a
 * question and goes to /api/ask. When both apply, the deterministic reading wins.
 */
export function routeInput(text: string, reading: TipReading, unknownCodes: readonly string[]): InputRoute {
  if (text.length > MAX_QUESTION_CHARS) return "tip";
  if (reading.claims.length > 0 || reading.promotionNotes.length > 0) return "tip";
  if (reading.stocks.length === 0 && unknownCodes.length > 0) return "tip";
  return "question";
}

// ---------------------------------------------------------------- result

export type TipNotice =
  | { kind: "unknown-code"; code: string; suggestions: string[]; total: number }
  | { kind: "no-code" }
  | { kind: "too-long" };

export interface ClaimRowView {
  key: string;
  title: string;
  line: string;
  verdict: Verdict | null;
  href: string;
}

export interface TipView {
  notices: TipNotice[];
  stocks: TipBundleStock[];
  /** Common-word codes seen without context: ask before showing them. */
  ambiguous: { code: string; prompt: string }[];
  claims: ClaimRowView[];
  /** Wording with no test behind it, quoted as sent. At most two. */
  untested: string[];
}

export const VERDICT_CHIP: Record<Verdict, string> = { yes: "Terbukti", no: "Tidak terbukti", mixed_or_inconclusive: "Belum jelas" };

/** The situation page a situation claim points to (tip-claims leaves some slugs null). */
const SITUATION_SLUG: Record<SituationId, string> = { spike: "harga-baru-melonjak", fall: "turun-banyak", ipo: "ikut-ipo", suspension: "pernah-disuspensi" };

const MAX_QUOTED = 40;

function quoted(text: string, phrase: string): string {
  const at = text.toLowerCase().indexOf(phrase.toLowerCase());
  const original = at >= 0 ? text.slice(at, at + phrase.length) : phrase;
  return original.length > MAX_QUOTED ? `${original.slice(0, MAX_QUOTED - 1)}…` : original;
}

export function buildTipView(text: string, reading: TipReading, bundle: TipBundle, unknownCodes: readonly string[], confirmed: readonly string[] = []): TipView {
  const byCode = new Map(bundle.stocks.map((s) => [s.code, s]));
  const codes = [...reading.stocks.map((s) => s.code), ...confirmed.filter((c) => !reading.stocks.some((s) => s.code === c))];
  const stocks = codes.map((c) => byCode.get(c)).filter((s): s is TipBundleStock => s !== undefined);
  const ambiguous = reading.ambiguous.filter((a) => !confirmed.includes(a.code)).map((a) => ({ code: a.code, prompt: a.prompt }));

  const claims: ClaimRowView[] = [];
  const seen = new Set<string>();
  const push = (row: ClaimRowView) => {
    if (seen.has(row.key)) return;
    seen.add(row.key);
    claims.push(row);
  };
  for (const claim of reading.claims) {
    if (claim.target.type === "finding") {
      for (const ref of claim.target.findings) {
        const f = bundle.findings.find((x) => (ref.pending ? x.hypothesisId === ref.ref : x.belief === ref.ref));
        if (f) push({ key: f.belief, title: f.title, line: f.line, verdict: f.verdict, href: `/temuan/${f.slug}` });
      }
    } else {
      const slug = SITUATION_SLUG[claim.target.situation];
      const s = bundle.situationClaims[claim.target.situation];
      if (s) push({ key: `situasi-${slug}`, title: claim.label, line: s.line, verdict: null, href: `/situasi/${s.slug}` });
    }
  }

  const untested: string[] = [];
  const addUntested = (phrase: string) => {
    const q = quoted(text, phrase);
    if (!untested.includes(q)) untested.push(q);
  };
  for (const note of reading.promotionNotes) if (note.category === "target" || note.category === "secret") note.phrases.forEach(addUntested);
  reading.unmatchedFragments.forEach(addUntested);

  const notices: TipNotice[] = [];
  if (reading.stocks.length === 0 && unknownCodes.length > 0) {
    const code = unknownCodes[0];
    notices.push({ kind: "unknown-code", code, suggestions: suggestCodes(code, bundle.stocks.map((s) => s.code)), total: bundle.stocks.length });
  } else if (stocks.length === 0 && ambiguous.length === 0) {
    notices.push({ kind: "no-code" });
  }
  if (reading.truncated) notices.push({ kind: "too-long" });

  return { notices, stocks, ambiguous, claims, untested: untested.slice(0, 2) };
}
