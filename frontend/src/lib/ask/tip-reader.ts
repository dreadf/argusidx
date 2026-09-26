import { commonWordTickers } from "./common-words";
import {
  PROMOTION_GUIDANCE,
  PROMOTION_NOTES,
  SENDER_QUESTIONS,
  compiledClaims,
  type ClaimKind,
  type PromotionCategory,
  type SituationId,
} from "./tip-claims";

/**
 * The "tip reader": turns a pasted tip message into structured results.
 * Pure and deterministic: no network, no LLM, no I/O, no shared state. The
 * pasted text is never sent anywhere by this module. Data (stocks, findings)
 * is injected so tests and the UI decide where it comes from.
 *
 * It never produces a score, a verdict, or advice. Findings are returned as
 * references, each standing on its own; the caller shows their own verdicts.
 */

export const MAX_TIP_CHARS = 2000;
export const MAX_STOCKS = 5;
export const MAX_AMBIGUOUS = 5;
export const MAX_FRAGMENTS = 8;
const MAX_FRAGMENT_CHARS = 140;

export interface TipStock {
  /** Bare ticker, e.g. "BBCA" (a trailing ".JK" is tolerated). */
  code: string;
  /** Registered name, e.g. "PT Bank Central Asia Tbk." */
  companyName: string;
}

/** Structurally compatible with FindingRow from findings-data.ts. */
export interface TipFinding {
  belief: string;
  evidence?: { hypothesis_id?: string };
}

export interface TipDeps {
  stocks: readonly TipStock[];
  findings: readonly TipFinding[];
}

export type MatchReason = "symbol-marker" | "jk-suffix" | "keyword" | "company-name" | "price-context" | "code";

export const MATCH_REASON_LABEL: Record<MatchReason, string> = {
  "symbol-marker": "Ditulis dengan tanda $ atau #",
  "jk-suffix": "Ditulis dengan akhiran .JK",
  keyword: "Didahului kata \"saham\" atau \"emiten\"",
  "company-name": "Nama perusahaan disebut",
  "price-context": "Ada harga atau target di dekatnya",
  code: "Kode saham dikenali",
};

// Strongest first.
const REASON_PRIORITY: MatchReason[] = ["symbol-marker", "jk-suffix", "keyword", "company-name", "price-context", "code"];

export interface TipStockMatch {
  code: string;
  companyName: string;
  matchedBy: MatchReason;
  /** The text as the sender wrote it. */
  mention: string;
}

export interface AmbiguousCandidate {
  code: string;
  companyName: string;
  /** Question for the reader to confirm. Never counted as a match. */
  prompt: string;
}

export interface FindingRef {
  /** The finding's `belief` key in findings.json, or a research id (e.g. "H6") when not yet published. */
  ref: string;
  /** True when the finding is not in the findings that were passed in. */
  pending: boolean;
  hypothesisIds: string[];
}

export type ResolvedTarget =
  | { type: "finding"; findings: FindingRef[] }
  | { type: "situation"; situation: SituationId; slug: string | null };

export interface MatchedClaim {
  id: string;
  kind: Exclude<ClaimKind, "promotion">;
  label: string;
  /** Verbatim-ish wording that triggered the match (lowercased, letters squeezed). */
  matchedText: string;
  target: ResolvedTarget;
}

export interface PromotionNote {
  category: PromotionCategory;
  note: string;
  phrases: string[];
}

export interface TipReading {
  originalLength: number;
  analyzedLength: number;
  /** True when the input was longer than MAX_TIP_CHARS and was cut. */
  truncated: boolean;
  /** At most MAX_STOCKS, in order of first appearance. */
  stocks: TipStockMatch[];
  /** True when more than MAX_STOCKS distinct stocks were found. */
  stocksOverflow: boolean;
  /** Distinct stocks found before the cap. */
  stocksFound: number;
  /** Common-word tickers seen without strong context. Never matches. */
  ambiguous: AmbiguousCandidate[];
  claims: MatchedClaim[];
  /** Sentences with no known claim: "Tidak ada data uji untuk: ..." Verbatim sender text. */
  unmatchedFragments: string[];
  promotionNotes: PromotionNote[];
  /** Neutral OJK guidance, present only when promotionNotes is not empty. */
  promotionGuidance: string | null;
  /** Fixed checklist, the same for every tip. */
  senderQuestions: readonly string[];
  /** Our own copy about limits of this reading (truncation, overflow). */
  notices: string[];
}

// ---------------------------------------------------------------- normalising

const EMOJI_RE = new RegExp("[\\p{Extended_Pictographic}\\u200d\\ufe0f\\u20e3\\u{1F3FB}-\\u{1F3FF}\\u{1F1E6}-\\u{1F1FF}]", "gu");
const CONTROL_RE = new RegExp("[^\\P{Cc}\\n]", "gu");

/** Cuts at MAX_TIP_CHARS without splitting a surrogate pair. */
function truncateSafely(text: string): { text: string; truncated: boolean } {
  if (text.length <= MAX_TIP_CHARS) return { text, truncated: false };
  let end = MAX_TIP_CHARS;
  const last = text.charCodeAt(end - 1);
  if (last >= 0xd800 && last <= 0xdbff) end -= 1;
  return { text: text.slice(0, end), truncated: true };
}

/** NFKC, emoji and control characters to spaces, repeated punctuation squeezed. Keeps case. */
function normalize(text: string): string {
  return text
    .normalize("NFKC")
    .replace(/\r\n?/g, "\n")
    .replace(EMOJI_RE, " ")
    .replace(CONTROL_RE, " ")
    .replace(/([!?.,;:*_~=-])\1+/g, "$1")
    .replace(/[ \t]+/g, " ");
}

/** For claim matching: lowercase, 3+ repeated letters squeezed to one ("mantuuul" -> "mantul"). */
function forClaims(s: string): string {
  return s.toLowerCase().replace(/([a-z])\1{2,}/g, "$1");
}

// ---------------------------------------------------------------- stock index

interface StockIndex {
  byCode: Map<string, TipStock>;
  common: Set<string>;
  names: { core: string; code: string }[];
}

const indexCache = new WeakMap<readonly TipStock[], StockIndex>();

function bareCode(code: string): string {
  return code.toUpperCase().replace(/\.JK$/, "");
}

function getIndex(stocks: readonly TipStock[]): StockIndex {
  const cached = indexCache.get(stocks);
  if (cached) return cached;
  const byCode = new Map<string, TipStock>();
  for (const s of stocks) byCode.set(bareCode(s.code), { code: bareCode(s.code), companyName: s.companyName });
  const common = new Set(commonWordTickers([...byCode.keys()]));
  const names: StockIndex["names"] = [];
  for (const s of byCode.values()) {
    const core = s.companyName
      .toLowerCase()
      .replace(/^pt\.?\s+/, "")
      .replace(/\s+tbk\.?$/, "")
      .trim();
    // Same rule as stock-lookup.ts: only multi-word names count, so a
    // one-word core that is an ordinary word ("timah") never matches.
    if (core.length >= 4 && core.includes(" ")) names.push({ core, code: s.code });
  }
  names.sort((a, b) => b.core.length - a.core.length || (a.code < b.code ? -1 : 1));
  const index = { byCode, common, names };
  indexCache.set(stocks, index);
  return index;
}

const isAlnum = (ch: string | undefined): boolean => ch !== undefined && /[a-z0-9]/i.test(ch);

const PRICE_CUE_RE = /^(tp\d*|tgt|target|sl|cl|entry|support|resist\w*|cutloss|rp\.?|@\d.*)$/i;
const NUMBER_RE = /^(rp\.?)?\d[\d.,]*(k|rb|ribu)?$/i;
const NUMBER_UNIT_RE = /^(juta|jt|miliar|triliun|lot|lembar|persen|hari|bulan|tahun|kali|orang|kg|ton|unit)$/i;
const KEYWORD_BEFORE_RE = /\b(saham|emiten|kode|ticker|tiker|stock|stocks|code)\s*[:-]?\s*$/i;
const TOKEN_SPLIT_RE = /[\s,;:!?()]+/;

function tokenAsCode(tok: string, index: StockIndex): boolean {
  return index.byCode.has(tok.toUpperCase().replace(/^[$#]/, "").replace(/\.JK$/i, ""));
}

/** A price or target next to the word, without crossing another ticker. */
function hasPriceContext(norm: string, start: number, end: number, index: StockIndex): boolean {
  const after = norm.slice(end, end + 60).split(TOKEN_SPLIT_RE).filter(Boolean).slice(0, 3);
  for (let i = 0; i < after.length; i++) {
    const tok = after[i];
    if (tokenAsCode(tok, index)) break;
    if (PRICE_CUE_RE.test(tok)) return true;
    const numberSlot = i === 0 || (i === 1 && /^(di|harga|@|=|rp\.?)$/i.test(after[0]));
    if (numberSlot && NUMBER_RE.test(tok) && !NUMBER_UNIT_RE.test(after[i + 1] ?? "")) return true;
  }
  const before = norm.slice(Math.max(0, start - 20), start).split(TOKEN_SPLIT_RE).filter(Boolean);
  const last = before[before.length - 1];
  return last !== undefined && PRICE_CUE_RE.test(last);
}

interface Found {
  code: string;
  position: number;
  mention: string;
  reason: MatchReason | null;
  upperOnly: boolean;
}

// ---------------------------------------------------------------- claims

const STOPWORDS = new Set(
  (
    "yang dan di ke dari ini itu untuk saya kita guys gan bro sis kak ya nih dong deh lho akan sudah udah bisa ada apa saja aja juga " +
    "atau dengan pada sama tapi kalau kalo jadi lagi mau buat sih kok yuk halo hai selamat pagi siang malam the and for you"
  ).split(" ")
);

function splitSegments(norm: string): string[] {
  return norm
    .split(/\n+|[.!?]+(?:\s+|$)/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function findingRefs(beliefs: readonly string[], pendingIds: readonly string[], findings: readonly TipFinding[]): FindingRef[] {
  const byBelief = new Map(findings.map((f) => [f.belief, f]));
  const refs: FindingRef[] = beliefs.map((belief) => {
    const f = byBelief.get(belief);
    return {
      ref: belief,
      pending: !f,
      hypothesisIds: (f?.evidence?.hypothesis_id ?? "").split(/[,\s]+/).filter(Boolean),
    };
  });
  for (const id of pendingIds) refs.push({ ref: id, pending: true, hypothesisIds: [id] });
  return refs;
}

// ---------------------------------------------------------------- main

export function readTip(text: string, deps: TipDeps): TipReading {
  const original = typeof text === "string" ? text : "";
  const cut = truncateSafely(original);
  const norm = normalize(cut.text);
  const lower = norm.toLowerCase();
  const index = getIndex(deps.stocks);

  // 1. company names (longest first; consumed ranges hide their inner words)
  const found: Found[] = [];
  const consumed: [number, number][] = [];
  for (const { core, code } of index.names) {
    let from = 0;
    for (;;) {
      const at = lower.indexOf(core, from);
      if (at === -1) break;
      const end = at + core.length;
      from = end;
      if (isAlnum(lower[at - 1]) || isAlnum(lower[end])) continue;
      if (consumed.some(([a, b]) => at < b && end > a)) continue;
      consumed.push([at, end]);
      found.push({ code, position: at, mention: norm.slice(at, end), reason: "company-name", upperOnly: false });
    }
  }

  // 2. ticker-shaped tokens
  const tokenRe = /([$#]?)([A-Za-z]{4})(\.jk)?(?![A-Za-z0-9])/gi;
  for (let m = tokenRe.exec(norm); m !== null; m = tokenRe.exec(norm)) {
    const start = m.index;
    const end = start + m[0].length;
    if (isAlnum(norm[start - 1])) continue;
    const code = m[2].toUpperCase();
    if (!index.byCode.has(code)) continue;
    if (consumed.some(([a, b]) => start < b && end > a)) continue;
    let reason: MatchReason | null = null;
    if (m[1]) reason = "symbol-marker";
    else if (m[3]) reason = "jk-suffix";
    else if (KEYWORD_BEFORE_RE.test(norm.slice(Math.max(0, start - 25), start))) reason = "keyword";
    else if (hasPriceContext(norm, start, end, index)) reason = "price-context";
    found.push({ code, position: start, mention: m[0], reason, upperOnly: m[2] === m[2].toUpperCase() });
  }
  found.sort((a, b) => a.position - b.position);

  // 3. decide per code
  const matches = new Map<string, TipStockMatch & { position: number }>();
  const ambiguousCodes = new Map<string, number>();
  for (const f of found) {
    const isCommon = index.common.has(f.code);
    const reason: MatchReason | null = f.reason ?? (isCommon ? null : "code");
    if (reason === null) {
      if (f.upperOnly && !ambiguousCodes.has(f.code)) ambiguousCodes.set(f.code, f.position);
      continue;
    }
    const stock = index.byCode.get(f.code)!;
    const prev = matches.get(f.code);
    if (!prev) {
      matches.set(f.code, { code: f.code, companyName: stock.companyName, matchedBy: reason, mention: f.mention, position: f.position });
    } else if (REASON_PRIORITY.indexOf(reason) < REASON_PRIORITY.indexOf(prev.matchedBy)) {
      prev.matchedBy = reason;
      prev.mention = f.mention;
    }
  }
  const ordered = [...matches.values()].sort((a, b) => a.position - b.position);
  const stocks: TipStockMatch[] = ordered.slice(0, MAX_STOCKS).map((s) => ({
    code: s.code,
    companyName: s.companyName,
    matchedBy: s.matchedBy,
    mention: s.mention,
  }));
  const ambiguous: AmbiguousCandidate[] = [...ambiguousCodes.entries()]
    .filter(([code]) => !matches.has(code))
    .sort((a, b) => a[1] - b[1])
    .slice(0, MAX_AMBIGUOUS)
    .map(([code]) => ({ code, companyName: index.byCode.get(code)!.companyName, prompt: `Maksud Anda saham ${code}?` }));

  // 4. claims, promotion phrases and unmatched sentences
  const claims: MatchedClaim[] = [];
  const claimSeen = new Set<string>();
  const promo = new Map<PromotionCategory, Set<string>>();
  const unmatched: string[] = [];
  const nonCommonCodes = new Set([...index.byCode.keys()].filter((c) => !index.common.has(c)).map((c) => c.toLowerCase()));

  for (const segment of splitSegments(norm)) {
    const seg = forClaims(segment);
    let hit = false;
    for (const { def, res } of compiledClaims()) {
      for (const re of res) {
        const m = re.exec(seg);
        if (!m) continue;
        hit = true;
        if (def.target.type === "promotion") {
          const set = promo.get(def.target.category) ?? new Set<string>();
          set.add(m[0].trim());
          promo.set(def.target.category, set);
        } else if (!claimSeen.has(def.id)) {
          claimSeen.add(def.id);
          const target: ResolvedTarget =
            def.target.type === "finding"
              ? { type: "finding", findings: findingRefs(def.target.beliefs, def.target.pendingIds, deps.findings) }
              : { type: "situation", situation: def.target.situation, slug: def.target.slug };
          claims.push({ id: def.id, kind: def.kind as MatchedClaim["kind"], label: def.label, matchedText: m[0].trim(), target });
        }
        break;
      }
    }
    if (hit) continue;
    const content = (seg.match(/[a-z]{3,}/g) ?? []).filter((w) => !STOPWORDS.has(w) && !nonCommonCodes.has(w));
    if (content.length >= 2 && unmatched.length < MAX_FRAGMENTS) {
      unmatched.push(segment.length > MAX_FRAGMENT_CHARS ? `${segment.slice(0, MAX_FRAGMENT_CHARS - 1)}…` : segment);
    }
  }

  const promotionNotes: PromotionNote[] = (["certainty", "urgency", "target", "secret"] as const)
    .filter((c) => promo.has(c))
    .map((category) => ({ category, note: PROMOTION_NOTES[category], phrases: [...promo.get(category)!].slice(0, 3) }));

  const notices: string[] = [];
  if (cut.truncated) notices.push(`Pesan terlalu panjang. Hanya 2.000 karakter pertama yang dibaca.`);
  if (ordered.length > MAX_STOCKS) notices.push(`Ada ${ordered.length} saham disebut. Hanya ${MAX_STOCKS} pertama yang ditampilkan.`);

  return {
    originalLength: original.length,
    analyzedLength: cut.text.length,
    truncated: cut.truncated,
    stocks,
    stocksOverflow: ordered.length > MAX_STOCKS,
    stocksFound: ordered.length,
    ambiguous,
    claims,
    unmatchedFragments: unmatched,
    promotionNotes,
    promotionGuidance: promotionNotes.length > 0 ? PROMOTION_GUIDANCE : null,
    senderQuestions: SENDER_QUESTIONS,
    notices,
  };
}
