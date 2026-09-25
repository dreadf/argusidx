/**
 * Per-tab navigation trail, so "back" leads to the page the user actually
 * came from instead of a fixed parent. sessionStorage only: it dies with the
 * tab, holds paths and nothing else, and a blocked store just means the
 * caller falls back to its default parent.
 */
const KEY = "argusidx:trail";
export const TRAIL_EVENT = "argusidx:trail-changed";
const MAX = 30;

let cached: string[] | null = null;

function read(): string[] {
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function trail(): string[] {
  if (cached === null) cached = read();
  return cached;
}

/** Records the page now shown. Revisiting the previous entry counts as going back (pops), anything else pushes. */
export function recordVisit(url: string): void {
  const t = trail();
  if (t[t.length - 1] === url) return;
  const next = t[t.length - 2] === url ? t.slice(0, -1) : [...t, url].slice(-MAX);
  cached = next;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Storage blocked: back falls back to the page's own parent.
  }
  window.dispatchEvent(new Event(TRAIL_EVENT));
}

/** The page before the current one, or null when this tab has no earlier page. */
export function getPreviousSnapshot(): string | null {
  const t = trail();
  return t.length >= 2 ? t[t.length - 2] : null;
}

export function getPreviousServerSnapshot(): string | null {
  return null;
}

export function subscribeTrail(onChange: () => void): () => void {
  window.addEventListener(TRAIL_EVENT, onChange);
  return () => window.removeEventListener(TRAIL_EVENT, onChange);
}

/** Short label for a path: what the user would call the page they are returning to. */
export function labelForPath(url: string): string {
  const path = url.split("?")[0].replace(/\/+$/, "") || "/";
  if (path === "/") return "Beranda";
  const seg = path.split("/").filter(Boolean);
  switch (seg[0]) {
    case "saham":
      return seg[1] ?? "Saham";
    case "jelajah":
      if (seg[1] === "sektor") return seg[3] === "saham" ? "Daftar saham" : "Sektor";
      if (seg[1] === "tanda") return "Tanda";
      if (seg[1] === "berita") return "Berita";
      return "Jelajah";
    case "situasi":
      return "Situasi";
    case "temuan":
      return seg[1] === "cara-kami-menguji" ? "Cara kami menguji" : "Temuan";
    case "tanya":
      return "Tanya";
    case "cari":
      return "Cari";
    case "watchlist":
      return "Watchlist";
    default:
      return "Kembali";
  }
}
