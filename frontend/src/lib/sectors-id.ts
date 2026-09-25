import type { LucideIcon } from "lucide-react";
import { Building2, Cpu, Factory, HeartPulse, Landmark, Layers, Route, ShoppingBag, ShoppingBasket, Truck, Zap } from "lucide-react";

/**
 * Sectors' sector names (English) -> Indonesian label, URL slug and icon.
 * The data files keep Sectors' names; only display goes through here.
 */
export interface SectorMeta {
  key: string;
  slug: string;
  label: string;
  icon: LucideIcon;
}

export const SECTOR_META: SectorMeta[] = [
  { key: "Consumer Cyclicals", slug: "konsumer-siklikal", label: "Konsumer Siklikal", icon: ShoppingBag },
  { key: "Consumer Non-Cyclicals", slug: "konsumer-non-siklikal", label: "Konsumer Non-Siklikal", icon: ShoppingBasket },
  { key: "Basic Materials", slug: "bahan-dasar", label: "Bahan Dasar", icon: Layers },
  { key: "Financials", slug: "keuangan", label: "Keuangan", icon: Landmark },
  { key: "Properties & Real Estate", slug: "properti", label: "Properti & Real Estat", icon: Building2 },
  { key: "Energy", slug: "energi", label: "Energi", icon: Zap },
  { key: "Infrastructures", slug: "infrastruktur", label: "Infrastruktur", icon: Route },
  { key: "Industrials", slug: "industri", label: "Industri", icon: Factory },
  { key: "Technology", slug: "teknologi", label: "Teknologi", icon: Cpu },
  { key: "Healthcare", slug: "kesehatan", label: "Kesehatan", icon: HeartPulse },
  { key: "Transportation & Logistic", slug: "transportasi", label: "Transportasi & Logistik", icon: Truck },
];

export function sectorByKey(key: string | null): SectorMeta | undefined {
  return SECTOR_META.find((s) => s.key === key);
}

export function sectorBySlug(slug: string): SectorMeta | undefined {
  return SECTOR_META.find((s) => s.slug === slug);
}
