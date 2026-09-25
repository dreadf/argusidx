/**
 * Number check for model-written prose: every figure in the answer must
 * already appear in the evidence it was given (or in the user's own
 * question). Figures are compared by value ("55,5" equals "55.5", but
 * "1,5" never equals "15"), so formatting cannot hide a changed number.
 * This is what makes "the model never produces a number" enforced instead
 * of hoped for.
 */
function canonical(raw: string): string {
  let s = raw.replace(/[.,]+$/, "");
  if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  else if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");
  const n = Number(s);
  return Number.isFinite(n) ? String(n) : s;
}

function numberTokens(text: string): string[] {
  return [...text.matchAll(/\d[\d.,]*/g)].map((m) => canonical(m[0]));
}

export function ungroundedNumbers(prose: string, sources: string[]): string[] {
  const allowed = new Set(sources.flatMap(numberTokens));
  return [...new Set(numberTokens(prose))].filter((t) => !allowed.has(t));
}
