import { PageTitle, UnderlineTabs } from "@/components/kit";

export type TemuanTab = "keyakinan" | "tanda" | "peringkat";

const TABS: { key: TemuanTab; label: string; href: string }[] = [
  { key: "keyakinan", label: "Keyakinan", href: "/temuan" },
  { key: "tanda", label: "Tanda", href: "/temuan/tanda" },
  { key: "peringkat", label: "Peringkat", href: "/temuan/peringkat" },
];

/** Shared top of the three Temuan lists: one title, one tab bar (board Baru3-Temuan-*). */
export function TemuanHead({ active, pill }: { active: TemuanTab; pill: string }) {
  return (
    <div>
      <PageTitle title="Temuan" pill={pill} />
      <div className="mt-4 md:mt-5">
        <UnderlineTabs items={TABS.map((t) => ({ label: t.label, href: t.href, active: t.key === active }))} />
      </div>
    </div>
  );
}
