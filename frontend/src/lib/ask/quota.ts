import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * Per-user allowance for AI-written answers: 3 per rolling 24 hours. Kept in a
 * signed cookie, not server memory, so it holds across serverless instances.
 * Clearing cookies resets it; the per-IP limit and the daily global cap in
 * rate-limit.ts stay as the backstop against that.
 */
export const QUOTA_LIMIT = 3;
export const QUOTA_WINDOW_MS = 24 * 60 * 60 * 1000;
export const QUOTA_COOKIE = "argus_ai";

export interface Quota {
  limit: number;
  remaining: number;
  /** ISO time when the oldest counted answer expires, or null when nothing is counted. */
  resetAt: string | null;
}

function secret(): string | null {
  return process.env.ASK_COOKIE_SECRET || process.env.GEMINI_API_KEY || null;
}

function sign(payload: string, key: string): string {
  return createHmac("sha256", key).update(payload).digest("base64url");
}

export function parseCookie(value: string | undefined, now = Date.now()): number[] {
  const key = secret();
  if (!value || !key) return [];
  const [payload, sig] = value.split(".");
  if (!payload || !sig) return [];
  const expected = Buffer.from(sign(payload, key));
  const given = Buffer.from(sig);
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) return [];
  try {
    const parsed: unknown = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8"));
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((t): t is number => typeof t === "number" && now - t < QUOTA_WINDOW_MS && t <= now).slice(-QUOTA_LIMIT);
  } catch {
    return [];
  }
}

export function serializeCookie(times: number[]): string {
  const key = secret() ?? "";
  const payload = Buffer.from(JSON.stringify(times)).toString("base64url");
  return `${payload}.${sign(payload, key)}`;
}

export function quotaFrom(times: number[]): Quota {
  return {
    limit: QUOTA_LIMIT,
    remaining: Math.max(0, QUOTA_LIMIT - times.length),
    resetAt: times.length > 0 ? new Date(times[0] + QUOTA_WINDOW_MS).toISOString() : null,
  };
}

export function readCookieHeader(request: Request): string | undefined {
  const header = request.headers.get("cookie");
  if (!header) return undefined;
  for (const part of header.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === QUOTA_COOKIE) return rest.join("=");
  }
  return undefined;
}
