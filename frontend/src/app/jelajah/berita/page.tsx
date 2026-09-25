import Link from "next/link";
import { Card, Cells, H2, Stat, Sub, TextLink } from "@/components/kit";
import { JelajahHead } from "@/components/jelajah-head";
import { RankList } from "@/components/rank-list";
import { formatDateId, idNum, shortName } from "@/lib/format";
import { getFindingsData } from "@/lib/findings-data";
import { getNewsSentiment } from "@/lib/news-data";

export default async function BeritaPage() {
  const [news, findings] = await Promise.all([getNewsSentiment(), getFindingsData()]);
  const newsFinding = findings.scoreboard.find((r) => r.belief === "Positive news coverage predicts a stock will rise");

  const summary = (
    <Card className="md:p-5">
      <Cells>{[<Stat key="a" value={idNum(news.n_articles, 0)} label="berita" size={26} />, <Stat key="b" value={idNum(news.n_symbols, 0)} label="saham disebut" size={26} />]}</Cells>
      <div className="my-4 h-px bg-border" />
      <div className="mb-2 text-xs text-muted-foreground">Dari {idNum(news.n_mentions, 0)} penyebutan saham</div>
      <Cells>
        {[
          <Stat key="p" value={`${idNum(news.bullish_mentions_pct, 0)}%`} label="bertanda bullish" tone="pos" size={24} />,
          <Stat key="n" value={`${idNum(100 - news.bullish_mentions_pct, 0)}%`} label="bertanda bearish" tone="neg" size={24} />,
        ]}
      </Cells>
    </Card>
  );

  const test = (
    <div>
      <div className="text-[15px] font-semibold">Apakah berita positif memprediksi kenaikan?</div>
      <div className="mt-2.5">
        <span className="inline-flex rounded-full border border-[var(--viz-status-warning)] px-2.5 py-0.5 text-xs font-semibold text-[var(--viz-status-warning)]">
          {newsFinding?.verdict === "mixed_or_inconclusive" ? "Belum jelas" : "Sudah diuji"}
        </span>
      </div>
      <TextLink href="/temuan?hasil=tidak-konsisten">Lihat hasil ujinya</TextLink>
    </div>
  );

  const limits = (
    <div>
      <div className="text-[15px] font-semibold">Batasan</div>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-[13.5px] leading-relaxed text-muted-foreground">
        <li>Hanya {Math.round((new Date(news.last_date).getTime() - new Date(news.first_date).getTime()) / 86_400_000 / 30)} bulan berita.</li>
        <li>Tanda bullish atau bearish dari Sectors, bukan dari kami.</li>
      </ul>
    </div>
  );

  const list = (
    <div>
      <H2>Paling banyak diberitakan</H2>
      <Sub>
        Angka kecil: <span className="text-[var(--viz-diverging-pos)]">bullish</span> &middot; <span className="text-[var(--viz-diverging-neg)]">bearish</span>.
      </Sub>
      <div className="mt-2">
        <RankList
          rows={news.most_covered.slice(0, 5).map((r) => ({
            code: r.symbol,
            name: shortName(r.company_name ?? r.symbol),
            value: idNum(r.mentions, 0),
            sub: (
              <>
                <span className="text-[var(--viz-diverging-pos)]">{r.bullish}</span> &middot; <span className="text-[var(--viz-diverging-neg)]">{r.bearish}</span>
              </>
            ),
          }))}
        />
      </div>
      <Link href="/jelajah?urut=banyak-diberitakan" className="mt-2 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
        Lihat 100 saham teratas &rarr;
      </Link>
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="berita" pill={`Data ${formatDateId(news.as_of)}`} />
      <Sub className="mt-4">
        Berita {formatDateId(news.first_date)} sampai {formatDateId(news.last_date)}.
      </Sub>
      <div className="mt-5 flex flex-col gap-5 md:mt-6 md:grid md:grid-cols-[1.3fr_1fr] md:gap-x-0 md:gap-y-0">
        <div className="contents md:flex md:min-w-0 md:flex-col md:pr-10">
          <div className="order-3 md:order-none">{list}</div>
        </div>
        <div className="contents md:flex md:min-w-0 md:flex-col md:gap-5 md:border-l md:border-border md:pl-10">
          <div className="order-1 md:order-none">{summary}</div>
          <div className="order-2 rounded-2xl border border-border bg-card p-4 md:order-none md:rounded-none md:border-0 md:bg-transparent md:p-0">{test}</div>
          <div className="order-4 md:order-none">{limits}</div>
        </div>
      </div>
    </main>
  );
}
