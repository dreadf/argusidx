import type { SituationId } from "./tip-claims";
import { SITUATION_SLUG, type ClaimRowView, type TipBundle, type TipBundleStock, type TipView } from "./tip-view";

/**
 * Sharing a checked message: the link carries only stock codes and claim ids
 * ("t~<finding slug>", "s~<situation id>"), never the message text. The page
 * behind it (/cek/[kode]) and its preview image (/api/og) rebuild the result
 * from the same data the app already ships, so a link cannot show anything
 * the app would not, and nothing a sender typed can travel in it.
 * Pure and browser-safe.
 */

export const MAX_SHARE_STOCKS = 3;
export const MAX_SHARE_CLAIMS = 6;

export const SITUATION_LABEL: Record<SituationId, string> = {
  spike: "Harga melonjak",
  fall: "Harga turun banyak",
  ipo: "IPO",
  suspension: "Habis suspensi",
};

export interface ShareTarget {
  codes: string[];
  keys: string[];
}

const CODE_RE = /^[A-Z0-9]{4}$/;
const KEY_RE = /^(?:t~[a-z0-9-]{1,60}|s~(?:spike|fall|ipo|suspension))$/;

/** What a result can share: at least one stock and one tested claim. Null otherwise (nothing useful to send). */
export function shareTargetOf(view: TipView): ShareTarget | null {
  const codes = [...new Set(view.stocks.map((s) => s.code))].slice(0, MAX_SHARE_STOCKS);
  const keys = [...new Set(view.claims.map((c) => c.share).filter((k): k is string => !!k))].slice(0, MAX_SHARE_CLAIMS);
  return codes.length > 0 && keys.length > 0 ? { codes, keys } : null;
}

export function sharePath(t: ShareTarget): string {
  return `/cek/${t.codes.join("-")}?k=${t.keys.map(encodeURIComponent).join(",")}`;
}

export function ogPath(t: ShareTarget): string {
  return `/api/og?kode=${t.codes.join("-")}&k=${t.keys.map(encodeURIComponent).join(",")}`;
}

/** Reads the URL parts back. Anything malformed is dropped, never guessed. Null when no valid stock code is left. */
export function parseShareParams(kode: string, k: string | null | undefined): ShareTarget | null {
  const codes = [...new Set(kode.toUpperCase().split("-").filter((c) => CODE_RE.test(c)))].slice(0, MAX_SHARE_STOCKS);
  if (codes.length === 0) return null;
  const keys = [...new Set((k ?? "").split(",").filter((x) => KEY_RE.test(x)))].slice(0, MAX_SHARE_CLAIMS);
  return { codes, keys };
}

export interface SharedResult {
  stocks: TipBundleStock[];
  claims: ClaimRowView[];
}

/** The stock cards and claim rows a link stands for, from bundle data only. Unknown codes and keys are skipped. */
export function resolveShare(bundle: TipBundle, target: ShareTarget): SharedResult {
  const byCode = new Map(bundle.stocks.map((s) => [s.code, s]));
  const stocks = target.codes.map((c) => byCode.get(c)).filter((s): s is TipBundleStock => s !== undefined);
  const claims: ClaimRowView[] = [];
  for (const key of target.keys) {
    if (key.startsWith("t~")) {
      const f = bundle.findings.find((x) => x.slug === key.slice(2));
      if (f) claims.push({ key: f.belief, title: f.title, line: f.line, verdict: f.verdict, href: `/temuan/${f.slug}`, share: key });
    } else {
      const id = key.slice(2) as SituationId;
      const s = bundle.situationClaims[id];
      if (s) claims.push({ key: `situasi-${SITUATION_SLUG[id]}`, title: SITUATION_LABEL[id], line: s.line, verdict: null, href: `/situasi/${s.slug}`, share: key });
    }
  }
  return { stocks, claims };
}

/** "BBCA: Saham oversold akan memantul", used as the link title. */
export function shareTitle(r: SharedResult): string {
  const codes = r.stocks.map((s) => s.code).join(", ");
  return r.claims[0] ? `${codes}: ${r.claims[0].title}` : `${codes}: hasil periksa`;
}
