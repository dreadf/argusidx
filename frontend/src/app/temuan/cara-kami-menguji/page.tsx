import { Page, PageTitle, Sub, TextLink } from "@/components/kit";
import { getFindingsData } from "@/lib/findings-data";
import { summarizeFindings, TRIAL_COUNT } from "@/lib/findings-summary";
import { formatDateId } from "@/lib/format";
import { getMarketData } from "@/lib/market-data";

/**
 * "Cara kami menguji": board "Cara-Menguji-2". Keyakinan and terbukti are
 * counted from data/app/findings.json; the trial count is the pinned
 * EXPERIMENT.md counter (lib/findings-summary.ts).
 */
const RULES = [
  { title: "Tulis dulu", line: "Aturan uji dicatat dengan tanggal sebelum hasilnya dilihat." },
  { title: "Dua data terpisah", line: "Ditemukan di data awal, diuji ulang di data yang belum dilihat." },
  { title: "Semua hasil tampil", line: "Yang gagal ditampilkan sama jelasnya." },
];

const LIMITS = [
  "Hanya perusahaan yang masih tercatat, jadi angka cenderung lebih baik dari kenyataan.",
  "Batas pada tanda diuji sampai +/-20% dan tidak diubah setelah melihat hasil.",
  "Beberapa uji punya data pendek, dan ditandai begitu.",
];

export default async function CaraKamiMengujiPage() {
  const [findings, market] = await Promise.all([getFindingsData(), getMarketData()]);
  const { beliefs, proven } = summarizeFindings(findings.scoreboard);
  const stats = [
    { value: TRIAL_COUNT, label: "uji", accent: false },
    { value: beliefs, label: "keyakinan", accent: false },
    { value: proven, label: "terbukti", accent: true },
  ];
  return (
    <Page>
      <PageTitle title="Cara kami menguji" pill={`Data ${formatDateId(market.as_of)}`} back={{ href: "/temuan", label: "Temuan" }} />
      <div className="md:max-w-3xl">
        <Sub>Bagaimana keyakinan diuji dan apa batasnya.</Sub>
        <div className="mt-4 flex gap-7">
          {stats.map((s) => (
            <div key={s.label}>
              <div className={`font-mono text-[28px] font-bold leading-none tabular-nums ${s.accent ? "text-[var(--viz-diverging-pos)]" : ""}`}>{s.value}</div>
              <div className="mt-1 text-xs text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </div>
        <ul className="mt-4 border-t border-border">
          {RULES.map((r) => (
            <li key={r.title} className="border-b border-border py-2.5">
              <div className="text-sm font-semibold leading-snug">{r.title}</div>
              <div className="mt-0.5 text-xs leading-normal text-muted-foreground">{r.line}</div>
            </li>
          ))}
        </ul>
        <h2 className="mt-6 text-lg font-bold leading-tight tracking-[-0.01em]">Batasan</h2>
        <ul className="mt-2.5 list-disc space-y-1 pl-[18px] text-[13.5px] leading-[1.7] text-muted-foreground">
          {LIMITS.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <div className="mt-2 flex flex-wrap gap-x-6">
          <TextLink href="/temuan">Catatan lengkap</TextLink>
          <TextLink href="/temuan/sumber-data">Sumber data</TextLink>
        </div>
      </div>
    </Page>
  );
}
