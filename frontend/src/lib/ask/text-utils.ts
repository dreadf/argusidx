/** Escapes regex metacharacters so arbitrary text (a keyword, a company
 * name fragment) can be dropped into a `new RegExp(...)` pattern safely —
 * shared by finding-topics.ts and stock-lookup.ts, both of which build a
 * `\bTEXT\b` word-boundary match against free-text questions. */
export function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
