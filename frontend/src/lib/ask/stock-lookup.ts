import { getAllStockCodes, getStockData } from "@/lib/stock-data";
import { escapeRegExp } from "./text-utils";

interface LookupEntry {
  code: string;
  nameCore: string;
  nameRe: RegExp;
  codeRe: RegExp;
}

let indexCache: LookupEntry[] | null = null;

/**
 * Builds (once, cached in module scope like stock-data.ts's own cache) a
 * plain index of {code, company name} for every one of the 962 companies,
 * used only to recognize which stock a free-text question is about.
 * Server-only — reads data/app/stocks.json via getStockData/getAllStockCodes.
 */
async function getLookupIndex(): Promise<LookupEntry[]> {
  if (indexCache) return indexCache;
  const codes = await getAllStockCodes();
  const entries: LookupEntry[] = [];
  for (const code of codes) {
    const data = await getStockData(code);
    if (!data) continue;
    // "PT Bank Central Asia Tbk." -> "bank central asia" (drop the PT/Tbk
    // wrapper so a question naming the company informally still matches).
    const nameCore = data.snapshot.company_name
      .toLowerCase()
      .replace(/^pt\.?\s+/, "")
      .replace(/\s+tbk\.?$/, "")
      .trim();
    entries.push({
      code,
      nameCore,
      nameRe: new RegExp(`\\b${escapeRegExp(nameCore)}\\b`),
      codeRe: new RegExp(`\\b${code}\\b`),
    });
  }
  indexCache = entries;
  return entries;
}

/**
 * Finds a single stock ticker mentioned in free text.
 *
 * Company-name match runs FIRST, not ticker match — some real IDX
 * tickers are ordinary words (e.g. `BANK`, PT Bank Aladin Syariah Tbk),
 * so "bagaimana kondisi Bank Central Asia?" must resolve to BBCA via its
 * company name before a ticker scan gets a chance to misfire on the word
 * "Bank" itself. A company-name match requires the fragment to be at
 * least 4 characters so short/generic name pieces ("PT", "Tbk") never
 * match. This reordering is a strict improvement over matching ticker
 * first (as this function used to): it can only resolve a question
 * *more* correctly, never less, since the ticker match below still runs
 * as a fallback when no company name is present.
 *
 * The name match additionally requires the stripped core to contain a
 * space (at least two words) and matches it as a whole word/phrase
 * (`\bcore\b`), never a bare substring — checked against the real
 * universe (2026-09-19): 23 companies reduce to a single-word core after
 * stripping PT/Tbk, and at least one, TINS.JK -> "Timah", is also the
 * ordinary Indonesian word for the metal tin. A plain substring match on
 * "timah" would misattribute any question about the commodity ("kenapa
 * harga timah dunia naik?") to that one stock. Multi-word cores ("bank
 * central asia") don't have this problem - a full company name appearing
 * verbatim is a deliberate signal, not a coincidence - so only
 * single-word cores are excluded from this path. Those 23 companies stay
 * reachable by their (case-sensitive) ticker below, or by the dedicated
 * search box (components/stock-search.tsx), the real general fix either way.
 *
 * Ticker match stays case-SENSITIVE (`\bBBCA\b`, capitals as typed) —
 * this was deliberately re-checked, not left as-is out of caution: a
 * direct scan of the real universe found 12 actual IDX tickers that are
 * ordinary Indonesian words used constantly in trading questions —
 * BANK, SATU, SEHAT, NAIK, LABA, EMAS, BELI, BUKA, BAIK, JAYA, MEGA,
 * AMAN. Matching lowercase would make "apakah harga akan naik?" or
 * "apakah datanya baik?" — completely ordinary phrasings — misfire on
 * NAIK/BAIK. That's a worse, broader version of the exact bug this
 * function was already fixed for once; making it case-insensitive would
 * reintroduce the same class of bug at 12x the surface area, not fix
 * anything. The real fix for "lowercase ticker lookup" is the dedicated
 * search box (components/stock-search.tsx) — an explicit picker where a
 * match is chosen by the user from a visible list, not inferred from
 * free text, so the same ambiguity never arises there.
 *
 * Returns null (not a guess) when nothing is unambiguous — an
 * unrecognized-ticker experience is safer than a wrong one.
 */
export async function findStockInText(text: string): Promise<string | null> {
  const index = await getLookupIndex();
  const lower = text.toLowerCase();

  // Longest matching name wins, so "Bumi Resources Minerals" is not read as
  // "Bumi Resources".
  let nameMatch: { code: string; length: number } | null = null;
  for (const entry of index) {
    if (entry.nameCore.length < 4 || !entry.nameCore.includes(" ")) continue;
    if (nameMatch && entry.nameCore.length <= nameMatch.length) continue;
    if (entry.nameRe.test(lower)) nameMatch = { code: entry.code, length: entry.nameCore.length };
  }
  if (nameMatch) return nameMatch.code;

  const tickerMatch = index.find((entry) => entry.codeRe.test(text));
  return tickerMatch?.code ?? null;
}
