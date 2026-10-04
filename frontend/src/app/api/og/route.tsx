import { ImageResponse } from "next/og";
import { parseShareParams, resolveShare } from "@/lib/ask/share";
import { getTipBundleFor } from "@/lib/ask/tip-bundle";
import { VERDICT_CHIP } from "@/lib/ask/tip-view";
import { formatDateId } from "@/lib/format";
import { getStocksAsOf } from "@/lib/stock-data";

/**
 * Link-preview card for a shared result (1200 x 630): the stock, the first
 * tested claim with its verdict and the one-line result. Built from the same
 * ids as the /cek page, so it holds nothing a sender typed.
 */
const COLOR = { yes: "#3987e5", no: "#e66767", mixed_or_inconclusive: "#fab219" } as const;

export async function GET(req: Request) {
  const sp = new URL(req.url).searchParams;
  const target = parseShareParams(sp.get("kode") ?? "", sp.get("k"));
  if (!target) return new Response("Tidak ditemukan", { status: 404 });
  const result = resolveShare(await getTipBundleFor(target.codes), target);
  const stock = result.stocks[0];
  const claim = result.claims[0];
  if (!stock || !claim) return new Response("Tidak ditemukan", { status: 404 });
  const asOf = formatDateId(await getStocksAsOf());
  const verdictColor = claim.verdict ? COLOR[claim.verdict] : "#8A97AD";
  const more = result.claims.length - 1;

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#0A0E17", color: "#F2F5FA", padding: "48px 60px", fontFamily: "sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", fontSize: 28, fontWeight: 700 }}>
          ArgusIDX
          <span style={{ marginLeft: 14, fontSize: 20, fontWeight: 400, color: "#8A97AD" }}>Periksa dulu</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", marginTop: 44 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 56, height: 56, borderRadius: 28, background: "rgba(27,87,196,0.3)", color: "#8FB4EE", fontSize: 18, fontWeight: 700 }}>{stock.code.slice(0, 2)}</div>
          <div style={{ display: "flex", flexDirection: "column", marginLeft: 16 }}>
            <div style={{ display: "flex", fontSize: 30, fontWeight: 700 }}>
              {result.stocks.map((s) => s.code).join(" · ")}
            </div>
            <div style={{ display: "flex", fontSize: 20, color: "#8A97AD" }}>
              {stock.short}
              {stock.price ? ` · ${stock.price}` : ""}
              {stock.change ? ` · ${stock.change}` : ""}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", fontSize: 58, fontWeight: 700, lineHeight: 1.12, marginTop: 36, maxWidth: 1000 }}>{claim.title}</div>
        <div style={{ display: "flex", alignItems: "center", marginTop: 30 }}>
          {claim.verdict && (
            <div style={{ display: "flex", fontSize: 28, fontWeight: 700, color: verdictColor, border: `2px solid ${verdictColor}`, borderRadius: 14, padding: "8px 22px" }}>{VERDICT_CHIP[claim.verdict]}</div>
          )}
          {more > 0 && <div style={{ display: "flex", fontSize: 22, color: "#8A97AD", marginLeft: 20 }}>{`+${more} klaim lain`}</div>}
        </div>
        <div style={{ display: "flex", fontSize: 28, lineHeight: 1.4, marginTop: 28, maxWidth: 1040, color: "#F2F5FA" }}>{claim.line}</div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, color: "#8A97AD", marginTop: "auto" }}>
          <span>{`Per ${asOf} · Bukan saran investasi`}</span>
          <span>argusidx.vercel.app</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
      headers: { "Cache-Control": "public, max-age=3600, s-maxage=86400" },
    },
  );
}
