import Link from "next/link";
import { ChevronRight, Check, Flag, LayoutGrid, MessageCircle, BarChart3, TrendingUp, X } from "lucide-react";
import { HomeSearch } from "@/components/home-search";
import { Eyebrow, Page } from "@/components/kit";
import { formatDateId } from "@/lib/format";
import { getFindingsData } from "@/lib/findings-data";
import { getMarketData } from "@/lib/market-data";
import { getSectorBreakdownData } from "@/lib/sector-data";
import { getSituationsFile, situationsOf } from "@/lib/stock-situations";
import { getSearchIndex } from "@/lib/stock-data";

const EXAMPLES = ["FILM", "ASII"];

/** Number step, 3 of them: board "Cara kerjanya". */
const STEPS = [
  { title: "Ketik kode", short: "Saham yang Anda punya, dengar, atau lirik.", long: "Ketik kode atau nama saham yang Anda punya, dengar, atau lirik." },
  { title: "Lihat situasi", short: "Jatuh dari puncak, rugi, disuspensi.", long: "Lihat situasi yang sedang dialaminya: jatuh dari puncak, rugi, disuspensi." },
  { title: "Lihat frekuensinya", short: "Dalam bentuk 88 dari 100.", long: "Lihat seberapa sering itu terjadi, dalam bentuk 88 dari 100, lengkap dengan batasnya." },
];

function Tilde() {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5 fill-none stroke-current" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 13c2.5-4 5-4 8 0s5.5 4 8 0" />
    </svg>
  );
}

/**
 * Beranda. Boards: Beranda-Baru-Mobile / Beranda-Baru-Web ("Beranda baru:
 * satu kotak"). One question box, how it works, the evidence count
 * (computed from data/app/findings.json), and ways in for people without
 * a stock in mind. The board has no Tanya entry, so one quiet link row was
 * added (requested in the milestone brief).
 */
export default async function Home() {
  const [findings, index, market, sectors, situationsFile] = await Promise.all([getFindingsData(), getSearchIndex(), getMarketData(), getSectorBreakdownData(), getSituationsFile()]);

  const total = findings.scoreboard.length;
  const count = { yes: 0, mixed_or_inconclusive: 0, no: 0 };
  for (const row of findings.scoreboard) count[row.verdict] += 1;
  const maxCount = Math.max(count.yes, count.mixed_or_inconclusive, count.no, 1);
  const bar = (n: number, max: number) => Math.max(6, Math.round((n / maxCount) * max));

  const exampleLine = EXAMPLES.map((code) => {
    const n = situationsOf(situationsFile, code).length;
    return n === 0 ? `${code} tidak ada.` : `${code} ada di ${n} situasi yang kami uji.`;
  }).join(" ");

  const asOf = formatDateId(market.as_of);
  const ways = [
    { href: "/jelajah", icon: BarChart3, title: "Peringkat", line: "Jauh dari puncak dan lainnya" },
    { href: "/jelajah/sektor", icon: LayoutGrid, title: "Sektor", line: `${sectors.sectors.length} sektor, daftar saham` },
    { href: "/jelajah/anomali", icon: Flag, title: "Deteksi anomali", line: "Kejadian tak biasa dan seberapa sering" },
    { href: "/jelajah/pasar", icon: TrendingUp, title: `Pasar per ${asOf.slice(0, 5)}`, line: "Nilai pasar, naik-turun" },
  ];

  const evidenceCard = (
    <div className="flex items-center gap-4 rounded-[18px] border border-border bg-card p-4">
      <div className="flex items-end gap-2.5" aria-hidden>
        {[
          { n: count.yes, color: "var(--viz-diverging-pos)", icon: <Check className="size-3.5" strokeWidth={1.7} /> },
          { n: count.mixed_or_inconclusive, color: "var(--viz-neutral, #5F6C84)", icon: <Tilde /> },
          { n: count.no, color: "var(--viz-diverging-neg)", icon: <X className="size-3.5" strokeWidth={1.7} /> },
        ].map((c, i) => (
          <div key={i} className="flex flex-col items-center justify-end gap-1">
            <span className="font-mono text-xs font-semibold">{c.n}</span>
            <div className="w-[26px] rounded-t-md rounded-b-[2px] md:w-7" style={{ height: bar(c.n, 57), background: c.color }} />
            <span className="flex text-muted-foreground">{c.icon}</span>
          </div>
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[14.5px] font-semibold leading-snug">
          Hanya {count.yes} dari {total} keyakinan saham yang terbukti
        </div>
        <p className="sr-only">
          {count.mixed_or_inconclusive} tidak konsisten, {count.no} tidak terbukti.
        </p>
        <Link href="/temuan" className="inline-flex min-h-9 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
          Lihat buktinya &rarr;
        </Link>
      </div>
    </div>
  );

  const rowLink = "flex min-h-12 items-center justify-between text-[13.5px] font-semibold text-[var(--viz-accent)]";

  return (
    <Page className="md:py-14">
      <section aria-label="Periksa saham" className="rounded-3xl border border-[var(--border-strong,rgba(255,255,255,0.14))] bg-card px-5 pb-[22px] pt-6 md:rounded-[28px] md:px-12 md:pb-10 md:pt-11">
        <div className="flex flex-col gap-4 md:gap-[18px]">
          <Eyebrow>Periksa dulu</Eyebrow>
          <h1 className="text-[30px] font-bold leading-[1.15] tracking-[-0.02em] md:text-[40px] md:leading-[1.12] md:tracking-[-0.025em]">Saham apa yang ingin Anda periksa?</h1>
          <p className="text-[14.5px] leading-relaxed text-muted-foreground md:text-base">Lihat situasi yang sedang dialaminya dan seberapa sering itu terjadi pada saham lain.</p>
          <HomeSearch index={index} examples={EXAMPLES} />
          <p className="text-[12.5px] text-muted-foreground">{exampleLine}</p>
        </div>
      </section>

      <div className="mt-11 md:mt-12 md:grid md:grid-cols-[0.95fr_1.3fr_1fr]">
        <section className="md:pr-9">
          <Eyebrow muted>Cara kerjanya</Eyebrow>
          <ol className="mt-3 grid grid-cols-3 gap-3 md:mt-3.5 md:grid-cols-1 md:gap-3.5">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <div className="flex items-center gap-1.5 md:hidden">
                  <span className="inline-flex size-[18px] shrink-0 items-center justify-center rounded-md bg-accent text-[10.5px] font-bold text-accent-foreground">{i + 1}</span>
                  <span className="text-xs font-semibold text-[var(--viz-ink-secondary,#B4BFD1)]">{s.title}</span>
                </div>
                <div className="mt-[5px] text-[11.5px] leading-normal text-muted-foreground md:hidden">{s.short}</div>
                <div className="hidden items-start gap-2.5 md:flex">
                  <span className="inline-flex size-[18px] shrink-0 items-center justify-center rounded-md bg-accent text-[10.5px] font-bold text-accent-foreground">{i + 1}</span>
                  <span className="text-[12.5px] leading-normal text-muted-foreground">{s.long}</span>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <div className="mt-11 border-t border-border pt-8 md:mt-0 md:border-l md:border-t-0 md:px-9 md:pt-0">
          <Eyebrow muted className="hidden md:block">Dasar dari angka-angkanya</Eyebrow>
          <div className="md:mt-3.5">{evidenceCard}</div>
          <Link href="/situasi" className={`${rowLink} mt-1 text-foreground`}>
            Semua situasi yang kami uji
            <ChevronRight className="size-[18px] text-muted-foreground" />
          </Link>
          <Link href="/tanya" className={`${rowLink} text-foreground`}>
            Punya pertanyaan sendiri? Tanya
            <MessageCircle className="size-[18px] text-muted-foreground" strokeWidth={1.7} />
          </Link>
        </div>

        <section className="mt-9 md:mt-0 md:border-l md:border-border md:pl-9">
          <h2 className="text-[15px] font-semibold leading-snug md:hidden">Belum punya saham?</h2>
          <Eyebrow muted className="hidden md:block">Belum punya saham?</Eyebrow>
          <p className="mb-3 mt-1 text-xs text-muted-foreground md:hidden">Jelajahi dulu, lalu buka salah satu sahamnya.</p>
          <div className="grid grid-cols-2 overflow-hidden rounded-2xl border border-border bg-card md:mt-3.5">
            {ways.map((w, i) => (
              <Link key={w.href} href={w.href} className={`flex flex-col gap-2 p-3.5 ${i % 2 === 0 ? "border-r border-border" : ""} ${i < 2 ? "border-b border-border" : ""}`}>
                <w.icon className="size-5 text-[var(--viz-accent)]" strokeWidth={1.7} />
                <span>
                  <span className="block text-sm font-semibold leading-snug">{w.title}</span>
                  <span className="mt-0.5 block text-[11.5px] text-muted-foreground">{w.line}</span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </Page>
  );
}
