import Link from "next/link";
import { JelajahHead } from "@/components/jelajah-head";
import { Sub } from "@/components/kit";
import { formatDateId } from "@/lib/format";
import { sectorByKey } from "@/lib/sectors-id";
import { getSectorBreakdownData } from "@/lib/sector-data";

export default async function SektorPage() {
  const data = await getSectorBreakdownData();
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="sektor" pill={`Data ${formatDateId(data.as_of)}`} />
      <Sub className="mt-4">Urut menurut jumlah perusahaan, bukan kinerja.</Sub>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-3.5 lg:grid-cols-4">
        {data.sectors.map((row) => {
          const meta = sectorByKey(row.sector);
          if (!meta) return null;
          const Icon = meta.icon;
          return (
            <Link
              key={row.sector}
              href={`/jelajah/sektor/${meta.slug}`}
              className="flex min-h-[110px] flex-col gap-2 rounded-2xl border border-border bg-card p-4 hover:border-[var(--viz-accent)]"
            >
              <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                <Icon className="size-5" strokeWidth={1.7} />
              </span>
              <span className="text-sm font-semibold leading-snug">{meta.label}</span>
              <span className="text-xs text-muted-foreground">{row.company_count} perusahaan</span>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
