import { readFile } from "node:fs/promises";
import path from "node:path";
import { idNum } from "@/lib/format";

interface Cell {
  n: number;
  rho: number;
  t: number;
  p: number;
}

interface RecheckFile {
  adjclose: Record<string, Cell | null>;
  close_research: Record<string, Cell | null>;
  sectors: Record<string, Cell | null>;
  verdict: Record<string, { replicated: boolean | null; price_source_inconsistent: boolean | null }>;
}

/** Findings that were re-checked on Sectors' own closing prices (EXPERIMENT.md, pre-registration "V"), by their belief text. */
const FEATURE_OF_BELIEF: Record<string, string> = {
  "Cheap stocks (low P/E) do better": "earnings_yield",
  "Small companies earn more": "size",
  "High dividend yield means better returns": "total_yield",
};

let cache: Promise<RecheckFile> | null = null;

function load(): Promise<RecheckFile> {
  cache ??= readFile(path.join(process.cwd(), "..", "data", "app", "sectors_recheck.json"), "utf-8").then((t) => JSON.parse(t) as RecheckFile);
  return cache;
}

const signed = (v: number) => `${v < 0 ? "-" : "+"}${idNum(Math.abs(v), 2)}`;
const pText = (p: number) => (p < 0.001 ? "di bawah 0,001" : idNum(p, p < 0.01 ? 3 : 2));

/** One or two plain sentences for a finding's page, or null if it was not re-checked. */
export async function recheckNote(belief: string): Promise<string | null> {
  const feature = FEATURE_OF_BELIEF[belief];
  if (!feature) return null;
  const f = await load();
  const s = f.sectors[feature];
  const r = f.adjclose[feature];
  if (!s || !r) return null;
  const v = f.verdict[feature];
  const base = "Diulang dengan harga penutupan dari Sectors pada data uji 2025 dan 2026.";
  if (v.replicated) {
    return `${base} Hasilnya sama: korelasi peringkat ${signed(s.rho)} (p ${pText(s.p)}), dibanding ${signed(r.rho)} pada riwayat harga riset.`;
  }
  return `${base} Pada harga Sectors, yang tidak memuat dividen, kaitannya hilang: korelasi peringkat ${signed(s.rho)} (p ${pText(s.p)}), dibanding ${signed(r.rho)} pada riwayat riset yang menghitung dividen sebagai bagian dari hasil.`;
}
