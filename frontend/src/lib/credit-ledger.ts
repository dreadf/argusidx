import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Credits used so far, from the "Running total" column of the last dated
 * table row in docs/credit_ledger.md. Pure parser + a server-only reader.
 */
export function parseLedgerTotal(markdown: string): number | null {
  const rows = markdown.split("\n").filter((l) => l.startsWith("| 20"));
  for (let i = rows.length - 1; i >= 0; i--) {
    const cells = rows[i].split("|").map((c) => c.trim());
    // A row starts and ends with "|", so the last real cell is second from the end.
    const total = Number(cells[cells.length - 2]?.replace(/[^\d]/g, ""));
    if (Number.isFinite(total) && total > 0) return total;
  }
  return null;
}

/** Null when the ledger cannot be read: the page then omits the figure rather than guess. */
export async function getCreditsUsed(): Promise<number | null> {
  try {
    const raw = await readFile(path.join(process.cwd(), "..", "docs", "credit_ledger.md"), "utf-8");
    return parseLedgerTotal(raw);
  } catch {
    return null;
  }
}
