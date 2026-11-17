// Which market this install serves (engine /region). Chicago is the fallback when the engine does not answer,
// so the Chicago site reads the same with or without it.
import { ENGINE_URL } from "./claim";

export type Region = {
  id: string;
  name: string;
  state: string;
  chicago: boolean;
  parcel_id_label: string;
  price_basis: string;
  parcel_source?: string | null;
  value_source?: string | null;
  zoning_source?: string | null;
  comps_source?: string | null;
  bounds?: [number, number, number, number] | null;
};

export const CHICAGO_REGION: Region = {
  id: "chicago",
  name: "Chicago",
  state: "IL",
  chicago: true,
  parcel_id_label: "PIN",
  price_basis: "recorded sales",
  bounds: [-87.94, 41.645, -87.524, 42.023],
};

let cached: { at: number; value: Region } | null = null;

export async function getRegion(): Promise<Region> {
  if (cached && Date.now() - cached.at < 60_000) return cached.value;
  try {
    const res = await fetch(`${ENGINE_URL}/region`, { cache: "no-store" });
    if (!res.ok) return CHICAGO_REGION;
    const r = (await res.json()) as Region;
    const value = r.chicago ? { ...CHICAGO_REGION, ...r, bounds: CHICAGO_REGION.bounds } : r;
    cached = { at: Date.now(), value };
    return value;
  } catch {
    return CHICAGO_REGION;
  }
}

// Cook County PINs print with dashes; other regions' parcel IDs print as stored.
export function showParcelId(region: Region, id: string): string {
  if (!region.chicago) return id;
  const d = id.replace(/\D/g, "");
  if (d.length === 14) return `${d.slice(0, 2)}-${d.slice(2, 4)}-${d.slice(4, 7)}-${d.slice(7, 10)}-${d.slice(10)}`;
  if (d.length === 10) return `${d.slice(0, 2)}-${d.slice(2, 4)}-${d.slice(4, 7)}-${d.slice(7, 10)}`;
  return id;
}
