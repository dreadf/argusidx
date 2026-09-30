import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { PageTitle, Sub } from "@/components/kit";
import { SituationGlyph } from "@/components/situation-glyph";
import { Note } from "@/components/situation-ui";
import { formatDateId, idNum } from "@/lib/format";
import { getSituations, type SituationGroup } from "@/lib/situations";
import { getSituationsFile } from "@/lib/stock-situations";

const GROUPS: SituationGroup[] = ["Harga", "Suspensi", "Laporan keuangan", "Penawaran baru", "Perbandingan"];

/**
 * Hub of the situations: what usually happens when you are in a
 * given circumstance. Reached from Beranda. Distinct from /temuan, which
 * asks whether a popular belief is true. Board: Situasi-Hub-2.
 */
export default async function SituasiPage() {
  const [situations, file] = await Promise.all([getSituations(), getSituationsFile()]);
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <div className="md:max-w-[860px]">
        <PageTitle title="Situasi" pill={`Data ${formatDateId(file.as_of)}`} />
        <Sub>{situations.length} keadaan saham, dan seberapa sering hal itu terjadi pada saham lain.</Sub>
        {GROUPS.map((group) => {
          const rows = situations.filter((s) => s.group === group);
          if (rows.length === 0) return null;
          return (
            <section key={group} className="mt-[22px]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">{group}</div>
              <div className="mt-1.5 border-t border-border">
                {rows.map((s) => (
                  <Link key={s.slug} href={`/situasi/${s.slug}`} className="flex items-center gap-3 border-b border-border py-3.5 transition-colors hover:bg-muted md:px-1">
                    <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
                      <SituationGlyph slug={s.slug} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[14.5px] font-semibold leading-snug">{s.title}</span>
                      <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{s.line}</span>
                    </span>
                    {s.count !== null && (
                      <span className="shrink-0 text-right">
                        <span className="block font-mono text-sm font-semibold">{idNum(s.count, 0)}</span>
                        <span className="block text-xs text-muted-foreground">saham</span>
                      </span>
                    )}
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
        <div className="mt-5">
          <Note>Kebiasaan masa lalu, bukan ramalan.</Note>
        </div>
      </div>
    </main>
  );
}
