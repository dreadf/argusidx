/**
 * Abuse guard for the one public, LLM-backed route (/api/ask). Two limits:
 *
 * 1. Per-IP request limit (sliding window) - stops one client hammering
 *    the route at all.
 * 2. A daily cap on calls that actually reach Gemini - past it, the route
 *    keeps answering from the deterministic template path (docs/PRODUCT.md
 *    section 0 rule 4), it just stops spending the API key.
 *
 * State is in module memory. On a serverless host each warm instance has
 * its own copy, so these are best-effort limits, not exact ones: a burst
 * spread across cold instances can exceed them. The real backstop against
 * runaway spend is a budget/quota cap on the Gemini key itself, set in the
 * Google console - this file only makes casual abuse expensive.
 */

const WINDOW_MS = 60_000;
/** 0 is a valid setting (a kill switch), so only an unset or non-numeric value falls back. */
function envNumber(name: string, fallback: number): number {
  const raw = process.env[name];
  const n = raw === undefined || raw.trim() === "" ? NaN : Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

const MAX_REQUESTS_PER_WINDOW = envNumber("ASK_MAX_PER_MINUTE", 10);
const GEMINI_DAILY_CAP = envNumber("GEMINI_DAILY_CAP", 300);
const IP_AI_WINDOW_MS = 6 * 60 * 60 * 1000;
const IP_AI_MAX = envNumber("GEMINI_MAX_PER_IP_6H", 9);
const aiHits = new Map<string, number[]>();
const MAX_TRACKED_IPS = 5_000;

const hits = new Map<string, number[]>();
let geminiDay = "";
let geminiCalls = 0;

export function clientIp(request: Request): string {
  // Client-controlled headers must not pick the bucket: the leftmost
  // x-forwarded-for entry and x-real-ip can be set by the caller unless a
  // proxy overwrites them. On Vercel the platform header is trusted;
  // elsewhere use the last x-forwarded-for hop, which the nearest proxy appends.
  if (process.env.VERCEL) {
    const platform = request.headers.get("x-vercel-forwarded-for");
    if (platform) return platform.split(",")[0].trim();
  }
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",").pop()?.trim() || "unknown";
  return request.headers.get("x-real-ip") ?? "unknown";
}

/** Gives back a slot reserved by reserveModelCall when the model call failed and produced nothing. */
export function releaseModelCall(ip: string): void {
  const times = aiHits.get(ip);
  if (times && times.length > 0) times.pop();
}

/** True if this IP is within its per-minute allowance (and records the hit). */
export function allowRequest(ip: string, now = Date.now()): boolean {
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  if (recent.length >= MAX_REQUESTS_PER_WINDOW) {
    hits.set(ip, recent);
    return false;
  }
  recent.push(now);
  hits.set(ip, recent);

  if (hits.size > MAX_TRACKED_IPS) {
    for (const [key, times] of hits) {
      if (times.every((t) => now - t >= WINDOW_MS)) hits.delete(key);
    }
  }
  return true;
}

/** True if a Gemini call is still allowed today (and counts it). */
export function allowGeminiCall(now = new Date()): boolean {
  const day = now.toISOString().slice(0, 10);
  if (day !== geminiDay) {
    geminiDay = day;
    geminiCalls = 0;
  }
  if (geminiCalls >= GEMINI_DAILY_CAP) return false;
  geminiCalls += 1;
  return true;
}

/**
 * Per-IP ceiling on model calls over 6 hours, a backstop behind the per-user
 * cookie allowance (which clearing cookies or replaying an old one defeats).
 * Reserves the slot before the call so parallel requests cannot all pass.
 */
export function reserveModelCall(ip: string, now = Date.now()): boolean {
  const recent = (aiHits.get(ip) ?? []).filter((t) => now - t < IP_AI_WINDOW_MS);
  if (recent.length >= IP_AI_MAX) {
    aiHits.set(ip, recent);
    return false;
  }
  recent.push(now);
  aiHits.set(ip, recent);
  if (aiHits.size > MAX_TRACKED_IPS) {
    for (const [key, times] of aiHits) {
      if (times.every((t) => now - t >= IP_AI_WINDOW_MS)) aiHits.delete(key);
    }
  }
  return true;
}
