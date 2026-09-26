import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { PageTitle, Sub, TextLink, UnderlineTabs } from "@/components/kit";
import { VerdictMark } from "@/components/verdict-mark";
import { sampleLine } from "@/lib/finding-copy";
import { findingSlug, getFindingsData, VERDICT_TAB, type Verdict } from "@/lib/findings-data";

const ORDER: Verdict[] = ["yes", "mixed_or_inconclusive", "no"];

/**
 * Temuan: "is this popular belief true?" One tab per outcome so the list
 * stays short. Situasi (reached from Beranda) answers a different
 * question: "what usually happens to me in this circumstance".
 */
export default async function TemuanPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const findings = await getFindingsData();
  const raw = Array.isArray(sp.hasil) ? sp.hasil[0] : sp.hasil;
  const active = ORDER.find((v) => VERDICT_TAB[v].key === raw) ?? "yes";
  const total = findings.scoreboard.length;
  const rows = findings.scoreboard.filter((r) => r.verdict === active);

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <PageTitle title="Temuan" pill="Data 13/09/2026" />
      <Sub>Apakah {total} keyakinan populer ini benar?</Sub>
      <TextLink href="/temuan/cara-kami-menguji" className="-mt-0.5">
        Cara kami menguji
      </TextLink>
      <div className="mt-2.5 md:mt-3">
        <UnderlineTabs
          items={ORDER.map((v) => ({
            label: VERDICT_TAB[v].label,
            href: `/temuan?hasil=${VERDICT_TAB[v].key}`,
            active: v === active,
            count: findings.scoreboard.filter((r) => r.verdict === v).length,
          }))}
        />
      </div>

      <div className="mt-4 hidden items-center gap-4 rounded-[10px] bg-[var(--viz-raised)] px-3 py-2.5 text-xs font-semibold tracking-[0.04em] text-[#B9C4D8] md:flex">
        <span className="w-6" />
        <span className="flex-[1.2]">Keyakinan</span>
        <span className="flex-1">Hasil pengujian</span>
        <span className="w-[170px]">Data</span>
        <span className="w-[18px]" />
      </div>
      <ul>
        {rows.map((row) => (
          <li key={row.belief}>
            <Link href={`/temuan/${findingSlug(row)}`} className="flex items-start gap-3 border-b border-border py-3.5 md:items-center md:gap-4 md:px-3 md:py-4">
              <span className="flex w-6 shrink-0 justify-center pt-0.5 md:pt-0">
                <VerdictMark verdict={row.verdict} />
              </span>
              <span className="min-w-0 flex-1 md:flex md:flex-1 md:items-center md:gap-4">
                <span className="block text-[15px] font-semibold leading-snug md:flex-[1.2]">{row.title_short_id}</span>
                <span className="mt-0.5 block text-[13px] leading-snug text-muted-foreground md:mt-0 md:flex-1 md:text-[13.5px]">{row.result_short_id}</span>
                <span className="mt-0.5 block text-[11.5px] text-muted-foreground md:mt-0 md:w-[170px] md:shrink-0 md:text-xs">{sampleLine(row.evidence)}</span>
              </span>
              <ChevronRight className="mt-1 size-[18px] shrink-0 text-muted-foreground md:mt-0" />
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
