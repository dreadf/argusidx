import { ChartNoAxesColumnDecreasing, ChartNoAxesColumnIncreasing, Flag, Pause, TrendingUp } from "lucide-react";
import { ExploreRow, GroupLabel, Note } from "@/components/explore-list";
import { JelajahHead } from "@/components/jelajah-head";
import { Sub } from "@/components/kit";
import { getAnomalyRows, type AnomalyGroup, type AnomalyIcon } from "@/lib/anomaly-data";
import { formatDateId } from "@/lib/format";

const ICONS: Record<AnomalyIcon, typeof Flag> = {
  spike: TrendingUp,
  pause: Pause,
  double: ChartNoAxesColumnIncreasing,
  decline: ChartNoAxesColumnDecreasing,
  flag: Flag,
};

const GROUPS: AnomalyGroup[] = ["Harga", "Laporan keuangan", "Dividen"];

/** Deteksi anomali: fixed-rule events, each with how often the follow-up happened. Counts and rates are read from data/app. */
export default async function AnomaliPage() {
  const { rows, asOf, situationSlugs } = await getAnomalyRows();
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="anomali" pill={`Data ${formatDateId(asOf)}`} />
      <Sub className="mt-4">Kejadian yang tidak biasa, dengan seberapa sering hal itu terjadi.</Sub>
      {GROUPS.map((group) => (
        <section key={group}>
          <GroupLabel>{group}</GroupLabel>
          {rows
            .filter((r) => r.group === group)
            .map((r) => {
              const Icon = ICONS[r.icon];
              // Situation page when it exists, else the flag page, else the situation index.
              const href = r.situationSlug && situationSlugs.has(r.situationSlug) ? `/situasi/${r.situationSlug}` : r.flagKind ? `/jelajah/anomali/${r.flagKind}` : "/situasi";
              return <ExploreRow key={r.key} href={href} title={r.title} isNew={r.isNew} line={r.line} icon={<Icon className="size-4" strokeWidth={1.7} />} />;
            })}
        </section>
      ))}
      <Note className="mt-5">Aturan tetap, bukan peringatan bahwa sesuatu buruk. Batas yang digeser 20% mengubah jumlahnya.</Note>
    </main>
  );
}
