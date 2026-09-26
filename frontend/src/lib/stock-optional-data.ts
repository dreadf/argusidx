import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Two "Data lengkap" rows of the boards that need data we do not have yet:
 * "Arus asing 20 hari" and "Harga IPO dibanding sekarang". Neither file
 * exists in data/app today, so both loaders return null and the rows do not
 * render (checked 2026-09-27). If the pipeline later writes them, the rows
 * appear without a code change. Shapes are what the page needs, nothing
 * more; a file that does not match returns null too. Server-only (fs).
 */

export interface ForeignFlow {
  /** ISO date of the last day counted. */
  as_of: string;
  /** Net foreign buying over the last 20 trading days, rupiah; negative is net selling. */
  net_idr: number;
}

export interface IpoPrice {
  /** Offer price at the IPO, rupiah. */
  offer_price: number;
  listing_date: string;
}

async function readBySymbol<T>(file: string, code: string, valid: (v: unknown) => v is T): Promise<T | null> {
  try {
    const raw = await readFile(path.join(process.cwd(), "..", "data", "app", file), "utf-8");
    const parsed = JSON.parse(raw) as { by_symbol?: Record<string, unknown> };
    const value = parsed.by_symbol?.[`${code}.JK`];
    return valid(value) ? value : null;
  } catch {
    return null;
  }
}

const isForeignFlow = (v: unknown): v is ForeignFlow => typeof v === "object" && v !== null && typeof (v as ForeignFlow).as_of === "string" && Number.isFinite((v as ForeignFlow).net_idr);
const isIpoPrice = (v: unknown): v is IpoPrice => typeof v === "object" && v !== null && Number.isFinite((v as IpoPrice).offer_price) && typeof (v as IpoPrice).listing_date === "string";

/** From data/app/foreign_flow.json (`by_symbol`), or null while that file does not exist. */
export function getForeignFlow(code: string): Promise<ForeignFlow | null> {
  return readBySymbol("foreign_flow.json", code, isForeignFlow);
}

/** From data/app/ipo_prices.json (`by_symbol`), or null while that file does not exist. */
export function getIpoPrice(code: string): Promise<IpoPrice | null> {
  return readBySymbol("ipo_prices.json", code, isIpoPrice);
}
