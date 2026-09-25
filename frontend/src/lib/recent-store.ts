/**
 * "Terakhir dilihat": the last few stock pages opened on this device.
 * Same storage rules as the watchlist: localStorage only, no account,
 * and a blocked or corrupt store just behaves as empty.
 */
const KEY = "argusidx:recent";
export const RECENT_EVENT = "argusidx:recent-changed";
const MAX = 5;

let cached: string[] | null = null;
const EMPTY: string[] = [];

function read(): string[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function getRecentSnapshot(): string[] {
  if (cached === null) cached = read();
  return cached;
}

export function getRecentServerSnapshot(): string[] {
  return EMPTY;
}

export function subscribeRecent(onChange: () => void): () => void {
  const handler = () => {
    cached = null;
    onChange();
  };
  window.addEventListener(RECENT_EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(RECENT_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

export function pushRecent(code: string): void {
  try {
    const next = [code, ...read().filter((c) => c !== code)].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(next));
    cached = null;
    window.dispatchEvent(new Event(RECENT_EVENT));
  } catch {
    // Storage blocked: recents are a convenience, never worth a crash.
  }
}
