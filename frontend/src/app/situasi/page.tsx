import { H2, LinkRow, Page, PageTitle, Sub, ThreeCol } from "@/components/kit";
import { getSituations, type SituationGroup } from "@/lib/situations";

const GROUPS: SituationGroup[] = ["Harga & penurunan", "Perusahaan & IPO", "Perbandingan"];

/**
 * Hub of the nine "situations": what usually happens when you are in a
 * given circumstance. Reached from Beranda. Distinct from /temuan, which
 * asks whether a popular belief is true.
 */
export default async function SituasiPage() {
  const situations = await getSituations();
  const columns = GROUPS.map((group) => (
    <div key={group}>
      <H2>{group}</H2>
      <div className="mt-1">
        {situations
          .filter((s) => s.group === group)
          .map((s, i, arr) => (
            <LinkRow key={s.slug} href={`/situasi/${s.slug}`} title={s.title} line={s.line} icon={<s.icon className="size-5" strokeWidth={1.7} />} last={i === arr.length - 1} />
          ))}
      </div>
    </div>
  ));
  return (
    <Page>
      <PageTitle title="Situasi" back={{ href: "/", label: "Beranda" }} />
      <Sub>Apa yang biasanya terjadi saat Anda mengalami ini.</Sub>
      <div className="mt-6 md:mt-7">
        <ThreeCol>{[columns[0], columns[1], columns[2]]}</ThreeCol>
      </div>
    </Page>
  );
}
