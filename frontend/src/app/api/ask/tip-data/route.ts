import { NextResponse } from "next/server";
import { getTipBundle } from "@/lib/ask/tip-bundle";

/**
 * Static data for reading a pasted message in the browser (stocks, findings,
 * situation lines). GET only, takes no input, so no user text ever reaches
 * the server: the message is read on the user's device.
 */
export async function GET() {
  return NextResponse.json(await getTipBundle(), { headers: { "Cache-Control": "public, max-age=3600" } });
}
