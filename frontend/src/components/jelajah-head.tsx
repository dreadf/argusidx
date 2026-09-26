import { PageTitle, UnderlineTabs } from "@/components/kit";

export type JelajahTab = "peringkat" | "sektor" | "anomali" | "pasar";

const TABS: { key: JelajahTab; label: string; href: string }[] = [
  { key: "peringkat", label: "Peringkat", href: "/jelajah" },
  { key: "sektor", label: "Sektor", href: "/jelajah/sektor" },
  { key: "anomali", label: "Deteksi anomali", href: "/jelajah/anomali" },
  { key: "pasar", label: "Pasar", href: "/jelajah/pasar" },
];

/** Shared top of every Jelajah page: one title, one tab bar. */
export function JelajahHead({ active, pill }: { active: JelajahTab; pill: string }) {
  return (
    <div>
      <PageTitle title="Jelajah" pill={pill} />
      <div className="mt-4 md:mt-5">
        <UnderlineTabs items={TABS.map((t) => ({ label: t.label, href: t.href, active: t.key === active }))} />
      </div>
    </div>
  );
}
