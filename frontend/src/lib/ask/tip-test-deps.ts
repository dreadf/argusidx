import { readFileSync } from "node:fs";
import path from "node:path";
import type { TipDeps, TipFinding, TipStock } from "./tip-reader";

/**
 * TEST-ONLY helper: loads the real data/app files into the shape readTip
 * expects. Not imported by any app code (it reads the disk).
 */
const dataDir = path.join(__dirname, "..", "..", "..", "..", "data", "app");

export function loadRealStocks(): TipStock[] {
  const raw = JSON.parse(readFileSync(path.join(dataDir, "stocks.json"), "utf-8")) as {
    stocks: Record<string, { snapshot: { company_name: string } }>;
  };
  return Object.entries(raw.stocks).map(([symbol, v]) => ({
    code: symbol.replace(/\.JK$/, ""),
    companyName: v.snapshot.company_name,
  }));
}

export function loadRealFindings(): TipFinding[] {
  const raw = JSON.parse(readFileSync(path.join(dataDir, "findings.json"), "utf-8")) as { scoreboard: TipFinding[] };
  return raw.scoreboard;
}

export function realDeps(): TipDeps {
  return { stocks: loadRealStocks(), findings: loadRealFindings() };
}
