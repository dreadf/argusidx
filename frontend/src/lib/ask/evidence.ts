import { GLOSSARY, type GlossaryKey } from "@/lib/glossary";
import { findingSlug, getFindingsData, type FindingRow } from "@/lib/findings-data";
import { formatDateId, idNum, pctFrom, shortName, signedPct } from "@/lib/format";
import { getMarketData } from "@/lib/market-data";
import { getRoeHistory } from "@/lib/roe-data";
import { getSituations } from "@/lib/situations";
import { getAllStockCodes, type StockPageData } from "@/lib/stock-data";
import { isRetested, sampleLine } from "@/lib/finding-copy";
import { formatPe, peVsSector } from "@/lib/pe";
import { fiveYearPhrase, pricePosition, relativeToTypical } from "@/lib/stock-summary";
import { matchFindingTopics } from "./finding-topics";
import { escapeRegExp } from "./text-utils";

/**
 * Retrieval for the Ask layer. Every fact the app can state about a question
 * is collected here as a short, self-contained sentence with an id, from the
 * same precomputed files the pages read. Nothing here calls a model. The
 * model (when on) may only rephrase these sentences; with the model off or
 * over its limit, the same sentences are shown as they are.
 */
export interface Evidence {
  id: string;
  kind: "saham" | "temuan" | "situasi" | "pasar" | "istilah";
  text: string;
  href?: string;
  linkLabel?: string;
}

export interface Retrieved {
  evidence: Evidence[];
  /** Findings whose wording matched the question by keyword (the deterministic route to a verdict). */
  keywordFindings: string[];
  findingRows: Map<string, FindingRow>;
}

const STOPWORDS = new Set(
  "yang dan atau apa apakah bagaimana berapa kenapa mengapa dari untuk dengan pada dalam ini itu saya kamu anda kita mereka bisa dapat tolong mohon jelaskan ringkasan singkat mudah dimengerti mengerti lebih agar supaya adalah ada tidak bukan akan sudah sedang masih juga saja hanya seperti terkait tentang soal sebuah para oleh kalau jika maka lagi nya lah kah punya minta boleh coba beri berikan tunjukkan".split(" "),
);

function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9/]+/)
    .filter((t) => t.length >= 3 && !STOPWORDS.has(t));
}

function wordMatches(q: string, words: Set<string>): boolean {
  if (words.has(q)) return true;
  return q.length >= 5 && [...words].some((w) => w.startsWith(q) || (w.length >= 5 && q.startsWith(w)));
}

/**
 * Weighted word overlap between the question and each document: a word that
 * appears in few documents counts more than one that appears in most
 * ("perusahaan", "saham"), so a question sharing only generic words retrieves
 * nothing instead of something irrelevant.
 */
function scoreDocs(queryTokens: string[], docs: string[]): number[] {
  const wordSets = docs.map((d) => new Set(tokens(d)));
  const weight = new Map<string, number>();
  for (const q of queryTokens) {
    const df = wordSets.filter((w) => wordMatches(q, w)).length;
    weight.set(q, df === 0 ? 0 : Math.log(1 + docs.length / df));
  }
  return wordSets.map((w) => queryTokens.filter((q) => wordMatches(q, w)).reduce((sum, q) => sum + (weight.get(q) ?? 0), 0));
}

const FINDING_MIN_SCORE = 3.5;

/** Everyday wording for each situation page; matched as plain phrases. */
const SITUATION_KEYWORDS: Record<string, string[]> = {
  "turun-banyak": ["turun banyak", "saham turun", "anjlok", "jatuh", "drawdown", "nyangkut", "rugi besar", "turun 30", "turun 40", "turun 50", "beli saat turun", "beli saat harga turun", "average down", "rata-rata turun", "pulih", "kembali naik", "balik ke harga", "serok"],
  "harga-baru-melonjak": ["melonjak", "naik tajam", "naik 40", "terbang", "roket", "harga baru naik"],
  "laba-turun-dua-tahun": ["laba turun dua tahun", "laba turun berturut", "laba menurun dua tahun"],
  "laba-dua-kali-lipat": ["laba dua kali lipat", "laba naik dua kali", "laba melonjak", "laba naik tajam"],
  "dekat-puncak-laba-turun": ["puncak", "tertinggi sepanjang masa", "all time high", "laba turun", "laba menurun"],
  "pernah-disuspensi": ["suspen", "dihentikan sementara", "digembok"],
  "perusahaan-rugi": ["rugi", "merugi", "laba negatif", "untung lagi", "balik untung", "turnaround"],
  "ikut-ipo": ["ipo", "penawaran umum", "papan akselerasi", "baru listing", "saham baru"],
  "dividen-besar": ["dividen besar", "dividen dipotong", "dipangkas", "payout", "dividen melebihi"],
  "float-tipis": ["float", "gorengan", "bergejolak", "saham tidur"],
  "vs-emas-deposito": ["emas", "deposito", "mengalahkan", "kalahkan", "lebih baik dari"],
};

const GLOSSARY_TRIGGERS: { key: GlossaryKey; re: RegExp }[] = [
  { key: "roe", re: /\broe\b/i },
  { key: "pe_ratio", re: /\bp\/e\b|\bpe\b/i },
  { key: "free_float", re: /free float/i },
  { key: "suspensi", re: /suspensi|disuspensi/i },
  { key: "ihsg", re: /\bihsg\b/i },
  { key: "payout_ratio", re: /payout|rasio pembayaran/i },
  { key: "dividend_yield", re: /dividend yield|yield dividen|imbal hasil dividen/i },
  { key: "lq45", re: /lq45/i },
  { key: "market_cap", re: /nilai pasar|kapitalisasi/i },
  { key: "peer_group", re: /sejenis|kelompok pembanding/i },
  { key: "casa_ratio", re: /\bcasa\b/i },
  { key: "loan_to_deposit_ratio", re: /\bldr\b/i },
  { key: "beat_gold", re: /\bemas\b/i },
];

function stockEvidence(code: string, d: StockPageData, ctx: { universe: number; roeSeries: string | null }): Evidence[] {
  const out: Evidence[] = [];
  const href = `/saham/${code}`;
  const add = (text: string) => out.push({ id: `S${out.length + 1}`, kind: "saham", text, href, linkLabel: `Halaman ${code}` });
  const { snapshot: s, sector_context: sc, peer_comparison: pc, flags, suspension_history: sh, insider_activity: ia, beat_gold: bg, lens_banking: lb, lens_extractive: le } = d;

  add(
    `${code} (${shortName(s.company_name)}) ada di sektor ${s.sector ?? "yang tidak diketahui"}${s.sub_sector ? `, sub-sektor ${s.sub_sector}` : ""}.` +
      (s.market_cap !== null
        ? ` Nilai pasarnya Rp ${idNum(s.market_cap / 1e12, 1)} triliun${s.market_cap_rank !== null ? `, terbesar ke-${s.market_cap_rank} dari ${ctx.universe} saham` : ""}.`
        : ""),
  );
  if (s.free_float !== null) add(`Free float ${code} ${idNum(s.free_float * 100, 1)}%: bagian saham yang dipegang publik.`);

  if (s.position_in_52w_range !== null && s.last_close_price !== null && s["52_w_high_price"] && s["52_w_low_price"] !== null) {
    const fromHigh = pctFrom(s.last_close_price, s["52_w_high_price"]);
    add(
      `Harga terakhir ${code} Rp ${s.last_close_price.toLocaleString("id-ID")}. Rentang setahun: terendah Rp ${s["52_w_low_price"].toLocaleString("id-ID")}, tertinggi Rp ${s["52_w_high_price"].toLocaleString("id-ID")}. ` +
        `Posisinya ${pricePosition(s.position_in_52w_range)?.toLowerCase()} rentang (${idNum(s.position_in_52w_range * 100, 0)}% dari dasar) dan ${signedPct(fromHigh)} dari tertinggi.`,
    );
  }

  if (sc && sc.own_roe_pct !== null && sc.sector_typical_roe_pct !== null) {
    add(
      `ROE ${code} ${idNum(sc.own_roe_pct)}%, ${relativeToTypical(sc.own_roe_pct, sc.sector_typical_roe_pct)} nilai tengah sektor ${sc.sector} (${idNum(sc.sector_typical_roe_pct)}%, dari ${sc.sector_roe_n} perusahaan yang melapor).`,
    );
  }
  if (pc && pc.better_than_count !== null && pc.comparable_count !== null) {
    add(`ROE ${code} lebih tinggi dari ${pc.better_than_count} dari ${pc.comparable_count} perusahaan sejenis di kelompok ${pc.group}.`);
  }
  if (sc && sc.own_pe !== null && sc.sector_typical_pe !== null) {
    const peRel = peVsSector(sc.own_pe, sc.sector_typical_pe);
    add(peRel === null ? `P/E ${code}: ${formatPe(sc.own_pe)}, jadi tidak dibandingkan dengan sektor.` : `P/E ${code} ${formatPe(sc.own_pe)}, ${peRel} nilai tengah sektor (${formatPe(sc.sector_typical_pe)}).`);
  }
  if (ctx.roeSeries) add(ctx.roeSeries);

  add(
    flags.length === 0
      ? `${code} tidak memicu satu pun dari 4 tanda dari laporan perusahaan.`
      : `${code} memicu ${flags.length} tanda dari 4: ${flags.map((f) => f.label.toLowerCase()).join("; ")}. Ini fakta dari laporan perusahaan, bukan penilaian.`,
  );

  add(
    sh
      ? `${code} pernah disuspensi ${sh.count} kali (penghentian sementara perdagangan oleh bursa), lebih sering dari ${idNum(sh.more_than_pct, 1)}% perusahaan. Di seluruh IDX, ${idNum(sh.base_rate_pct, 1)}% perusahaan pernah disuspensi.`
      : `${code} belum pernah disuspensi.`,
  );

  if (ia) {
    const dir = ia.net_direction === "net_buying" ? "lebih banyak membeli" : ia.net_direction === "net_selling" ? "lebih banyak menjual" : "seimbang antara beli dan jual";
    add(`Transaksi insider ${code} (direksi, komisaris, pemegang besar): ${ia.buy_count} pembelian dan ${ia.sell_count} penjualan tercatat, ${dir}.`);
  }

  if (bg) {
    const { won, lost } = fiveYearPhrase(bg);
    if (won.length + lost.length > 0) {
      add(
        `Riwayat harga ${bg.years} tahun (data historis yang dibekukan, bukan prediksi): ${won.length ? `menang dari ${won.join(" dan ")}` : ""}${won.length && lost.length ? ", " : ""}${lost.length ? `kalah dari ${lost.join(" dan ")}` : ""}.`,
      );
    }
  }
  if (lb?.ratios["casa_ratio[2025]"]) {
    const r = lb.ratios["casa_ratio[2025]"];
    add(`Rasio CASA ${code} ${idNum(r.value * 100, 1)}%, lebih tinggi dari ${r.better_than_count} dari ${r.comparable_count} bank lain.`);
  }
  if (lb?.loan_to_deposit_ratio != null) add(`Rasio kredit terhadap simpanan (LDR) ${code} ${idNum(lb.loan_to_deposit_ratio * 100, 0)}%.`);
  if (le) add(`${code} terkait komoditas: ${le.commodity_type.join(", ") || "tidak diketahui"}.`);
  return out;
}

export async function retrieveEvidence(question: string, stockCode: string | null, stockData: StockPageData | null): Promise<Retrieved> {
  const evidence: Evidence[] = [];
  const qTokens = tokens(question);
  const q = question.toLowerCase();

  if (stockCode && stockData) {
    const [roe, universe] = await Promise.all([getRoeHistory(stockCode, stockData.snapshot.sector), getAllStockCodes()]);
    let roeSeries: string | null = null;
    if (roe) {
      const pairs = roe.years.map((y, i) => [y, roe.own[i]] as const).filter((p): p is readonly [number, number] => p[1] !== null);
      if (pairs.length >= 2 && pairs.every((p) => Math.abs(p[1]) <= 150)) {
        roeSeries = `ROE ${stockCode} per tahun: ${pairs.map(([y, v]) => `${y} ${idNum(v)}%`).join(", ")}.`;
      }
    }
    evidence.push(...stockEvidence(stockCode, stockData, { universe: universe.length, roeSeries }));
  }

  const [findings, situations] = await Promise.all([getFindingsData(), getSituations()]);
  const keyword = matchFindingTopics(question);
  const rows = new Map<string, FindingRow>();
  const findingScores = scoreDocs(qTokens, findings.scoreboard.map((r) => `${r.belief_id} ${r.title_short_id} ${r.result_short_id}`));
  const scored = findings.scoreboard
    .map((row, i) => ({ row, score: keyword.includes(row.belief) ? 99 : findingScores[i] }))
    .filter((x) => x.score >= FINDING_MIN_SCORE)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
  scored.forEach(({ row }, i) => {
    const id = `T${i + 1}`;
    rows.set(id, row);
    const verdict = row.verdict === "yes" ? "terbukti" : row.verdict === "no" ? "tidak terbukti" : "tidak konsisten";
    evidence.push({
      id,
      kind: "temuan",
      text: `Keyakinan yang diuji: "${row.title_short_id}". Hasil: ${verdict}, ${row.result_short_id.toLowerCase()}. Sampel: ${sampleLine(row.evidence)}${isRetested(row.evidence) ? " (diuji ulang pada data terpisah)" : ""}. Periode: ${row.evidence.period_id}. Batasan: ${row.evidence.limit_id}`,
      href: `/temuan/${findingSlug(row)}`,
      linkLabel: "Buktinya",
    });
  });

  situations
    .map((s) => ({ s, score: (SITUATION_KEYWORDS[s.slug] ?? []).filter((k) => new RegExp(`\\b${escapeRegExp(k)}`).test(q)).length }))
    .filter((x) => x.score >= 1)
    .sort((a, b) => b.score - a.score)
    .slice(0, 2)
    .forEach(({ s }, i) => {
      evidence.push({
        id: `P${i + 1}`,
        kind: "situasi",
        text: `Situasi "${s.title}": ${s.explain} Batasan: ${s.limits.join(" ")}`,
        href: `/situasi/${s.slug}`,
        linkLabel: s.title,
      });
    });

  if (/\b(pasar|ihsg|indeks|hari ini|naik turun|market)\b/.test(q)) {
    const m = await getMarketData();
    evidence.push({
      id: "M1",
      kind: "pasar",
      text: `Per ${formatDateId(m.as_of)}: ${m.movers.up} saham naik, ${m.movers.down} turun, ${m.movers.flat} tetap. Posisi harga terhadap rentang setahun: ${m.breadth.near_high} dekat tertinggi, ${m.breadth.middle} di tengah, ${m.breadth.near_low} dekat terendah (dari ${m.breadth.total_evaluable} saham yang bisa dihitung).`,
      href: "/",
      linkLabel: "Beranda",
    });
  }

  // Plain definitions for jargon that the collected facts (or the question) use.
  const haystack = `${question} ${evidence.map((e) => e.text).join(" ")}`;
  let n = 0;
  for (const { key, re } of GLOSSARY_TRIGGERS) {
    if (n >= 4) break;
    if (re.test(haystack)) evidence.push({ id: `I${++n}`, kind: "istilah", text: `Arti istilah: ${GLOSSARY[key]}` });
  }

  return { evidence, keywordFindings: keyword, findingRows: rows };
}
