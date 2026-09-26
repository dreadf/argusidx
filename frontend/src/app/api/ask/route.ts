import { NextResponse } from "next/server";
import { containsAdviceLanguage } from "@/lib/ask/advice-language-guard";
import { classify, type Bucket } from "@/lib/ask/classify";
import { retrieveEvidence, type Evidence } from "@/lib/ask/evidence";
import { askGemini, type HistoryTurn } from "@/lib/ask/gemini-client";
import { ungroundedNumbers } from "@/lib/ask/grounding";
import { QUOTA_COOKIE, QUOTA_WINDOW_MS, parseCookie, quotaFrom, readCookieHeader, serializeCookie } from "@/lib/ask/quota";
import { allowGeminiCall, allowRequest, clientIp, releaseModelCall, reserveModelCall } from "@/lib/ask/rate-limit";
import { buildStockCard } from "@/lib/ask/stock-card";
import { findStockInText } from "@/lib/ask/stock-lookup";
import { buildTemplateProse } from "@/lib/ask/template-answers";
import type { AskResponse } from "@/lib/ask/types";
import { getAllStockCodes, getStockData } from "@/lib/stock-data";

const MAX_QUESTION_LENGTH = 300;
const MAX_HISTORY = 2;

/**
 * The one server-side function this product runs; everything else is
 * precomputed files. Retrieval-augmented in the plain sense: facts are
 * retrieved from data/app/*.json (evidence.ts), and a model, when one is
 * configured and the user still has allowance, only words an answer from
 * them. With no model, or past the limit, the same facts are shown as they
 * are (docs/PRODUCT.md §0 rule 4). Never calls Sectors live.
 */
export async function POST(request: Request) {
  if (!allowRequest(clientIp(request))) {
    return NextResponse.json({ error: "Terlalu banyak pertanyaan dalam waktu singkat. Coba lagi sebentar lagi." }, { status: 429 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body harus JSON." }, { status: 400 });
  }

  const question = (body as { question?: unknown })?.question;
  if (typeof question !== "string" || question.trim().length === 0) {
    return NextResponse.json({ error: "Pertanyaan tidak boleh kosong." }, { status: 400 });
  }
  if (question.length > MAX_QUESTION_LENGTH) {
    return NextResponse.json({ error: `Pertanyaan terlalu panjang (maks ${MAX_QUESTION_LENGTH} karakter).` }, { status: 400 });
  }
  const { history, carriedStock } = parseHistory((body as { history?: unknown })?.history);
  // "data": the user chose to be answered from data only. The model is not called and no allowance is spent.
  const wantsModel = (body as { mode?: unknown })?.mode !== "data";

  try {
    const now = Date.now();
    const usedTimes = parseCookie(readCookieHeader(request), now);
    const modelConfigured = Boolean(process.env.GEMINI_API_KEY);
    const modelOn = modelConfigured && wantsModel;

    const named = await findStockInText(question);
    const stockCode = named ?? (carriedStock && (await getStockData(carriedStock)) ? carriedStock : null);
    const stockData = stockCode ? await getStockData(stockCode) : null;

    const deterministic = classify(question, stockData !== null);
    let retrieved = await retrieveEvidence(question, stockCode, stockData);
    // A follow-up with no topic of its own ("jelaskan lebih sederhana") reuses the previous question's topic.
    if (retrieved.evidence.length === 0 && history.length > 0) {
      retrieved = await retrieveEvidence(`${history[history.length - 1].q} ${question}`, stockCode, stockData);
    }
    const stockEvidence = retrieved.evidence.filter((e) => e.kind === "saham");
    const matchedFindings = [...retrieved.findingRows.values()].filter((r) => retrieved.keywordFindings.includes(r.belief));

    // What the answer shows when the model does not write it.
    let bucket: Bucket = deterministic.bucket;
    let shown: Evidence[] = [];
    if (bucket === "finding") {
      // The verdict rows, plus the stock's own facts when the question is about a stock ("berapa ROE BBCA").
      shown = [...retrieved.evidence.filter((e) => e.kind === "temuan" && matchedFindings.includes(retrieved.findingRows.get(e.id)!)), ...stockEvidence];
    }
    else if (bucket === "untested_data") shown = stockEvidence;
    else if (bucket === "advice_seeking" || bucket === "unanswerable") shown = stockEvidence;
    else if (retrieved.evidence.some((e) => e.kind === "situasi" || e.kind === "pasar")) {
      // Without the model, only wording-matched situations and market facts are shown; loose word overlap is left to the model to judge.
      bucket = "answered";
      shown = retrieved.evidence.filter((e) => e.kind === "situasi" || e.kind === "pasar");
    }
    let prose = buildTemplateProse(bucket, stockCode, matchedFindings);
    let source: AskResponse["source"] = "template";
    let usedIds: string[] | null = null;

    const refused = deterministic.bucket === "advice_seeking" || deterministic.bucket === "unanswerable";
    const skipModel = refused || deterministic.bucket === "ambiguous" || retrieved.evidence.length === 0;
    const allowance = quotaFrom(usedTimes);
    const limitReached = modelOn && !skipModel && allowance.remaining === 0;
    let modelFailed = false;

    let newTimes = usedTimes;
    if (modelOn && !skipModel && !limitReached && !(reserveModelCall(clientIp(request), now) && allowGeminiCall())) modelFailed = true;
    else if (modelOn && !skipModel && !limitReached) {
      const result = await askGemini(question, history, retrieved.evidence);
      if (!result) {
        releaseModelCall(clientIp(request));
        modelFailed = true;
      }
      if (result && (result.bucket === "advice_seeking" || result.bucket === "unanswerable")) {
        // The model spotted a request for advice or a forecast that the wording patterns missed: use the fixed refusal.
        bucket = result.bucket;
        prose = buildTemplateProse(bucket, stockCode, matchedFindings);
        shown = stockEvidence;
      } else if (result) {
        const ids = new Set(retrieved.evidence.map((e) => e.id));
        const validIds = result.used_ids.filter((id) => ids.has(id));
        const sources = [question, ...retrieved.evidence.map((e) => e.text)];
        const okBucket = result.bucket === "answered" || result.bucket === "no_data";
        const contradictsKeyword = result.bucket === "no_data" && matchedFindings.length > 0;
        const ungrounded = ungroundedNumbers(result.prose, sources);
        const rejected = !okBucket ? `bucket ${result.bucket}` : contradictsKeyword ? "no_data despite keyword finding" : containsAdviceLanguage(result.prose) ? "advice language" : looksLikeInjectionArtifact(result.prose) ? "injection artifact" : ungrounded.length > 0 ? `ungrounded numbers ${ungrounded.join(",")}` : null;
        if (rejected === null) {
          newTimes = [...usedTimes, now];
          bucket = result.bucket === "answered" ? "answered" : "no_data";
          prose = result.prose;
          source = "gemini";
          usedIds = validIds.length > 0 ? validIds : result.bucket === "answered" ? retrieved.evidence.filter((e) => e.kind !== "istilah").slice(0, 4).map((e) => e.id) : [];
        } else {
          console.warn(`/api/ask: model answer rejected (${rejected}), using template`);
          modelFailed = true;
        }
      }
    }

    const chosen = usedIds ? retrieved.evidence.filter((e) => usedIds!.includes(e.id)) : shown;
    const facts = chosen.filter((e) => e.kind !== "temuan" && e.kind !== "istilah").map((e) => e.text).slice(0, bucket === "finding" ? 4 : 8);
    const findings = chosen.filter((e) => e.kind === "temuan").map((e) => retrieved.findingRows.get(e.id)!).filter(Boolean);
    const seen = new Set<string>();
    const links = chosen
      .filter((e) => e.href && e.linkLabel && !(e.kind === "saham"))
      .filter((e) => (seen.has(e.href!) ? false : (seen.add(e.href!), true)))
      .slice(0, 3)
      .map((e) => ({ label: e.linkLabel!, href: e.href! }));

    // Why the answer came from data when the user asked for AI: shown as one note under it.
    const notice: AskResponse["notice"] = !wantsModel ? null : limitReached ? "limit" : !modelConfigured || modelFailed ? "unavailable" : null;
    const card = stockCode && stockData ? buildStockCard(stockCode, stockData, (await getAllStockCodes()).length) : null;

    const response: AskResponse = {
      bucket,
      stockCode,
      card,
      notice,
      prose,
      facts,
      findings,
      links,
      source,
      quota: modelConfigured ? quotaFrom(newTimes) : null,
      limitReached,
    };
    const res = NextResponse.json(response);
    if (modelConfigured && newTimes !== usedTimes) {
      res.cookies.set(QUOTA_COOKIE, serializeCookie(newTimes), { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: Math.ceil(QUOTA_WINDOW_MS / 1000) });
    }
    return res;
  } catch (e) {
    console.error("POST /api/ask: unexpected error", e);
    return NextResponse.json({ error: "Terjadi kesalahan saat memproses pertanyaan." }, { status: 500 });
  }
}

/** Current allowance for this user, so the page can show the counter before the first question. Costs nothing and calls no model. */
export async function GET(request: Request) {
  const quota = process.env.GEMINI_API_KEY ? quotaFrom(parseCookie(readCookieHeader(request))) : null;
  return NextResponse.json({ quota }, { headers: { "Cache-Control": "no-store" } });
}

/** Last few turns sent by the page, used only to resolve "ini" and "itu" and to rephrase, never as a source of facts. */
function parseHistory(raw: unknown): { history: HistoryTurn[]; carriedStock: string | null } {
  if (!Array.isArray(raw)) return { history: [], carriedStock: null };
  const turns = raw
    .slice(-MAX_HISTORY)
    .map((t) => t as { q?: unknown; a?: unknown; stockCode?: unknown })
    .filter((t) => typeof t.q === "string" && typeof t.a === "string");
  const history = turns.map((t) => ({ q: (t.q as string).slice(0, MAX_QUESTION_LENGTH), a: (t.a as string).slice(0, 700) }));
  const last = [...turns].reverse().find((t) => typeof t.stockCode === "string" && /^[A-Z0-9]{4}$/.test(t.stockCode as string));
  return { history, carriedStock: last ? (last.stockCode as string) : null };
}

/**
 * Prompt-injection containment, output side (paired with the delimiting in
 * gemini-client.ts). If the delimiter markers or an obvious system-prompt
 * echo show up in the output, something in the input confused the model:
 * reject and use the template rather than reflect it back.
 */
function looksLikeInjectionArtifact(prose: string): boolean {
  return /---[A-Z_]+---|ATURAN KETAT|responseSchema|BUKTI \(satu-satunya/i.test(prose);
}
