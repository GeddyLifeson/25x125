import { getCommunityAreas, settle } from "../../lib/engine";
import { getRegion } from "../../lib/region";
import { MapScreen } from "./MapScreen";

export const dynamic = "force-dynamic";
export const metadata = { title: "25x125 map and list" };

export default async function MapPage({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  const areas = await settle(getCommunityAreas());
  const region = await getRegion();
  return (
    <>
      {!areas.ok && <p className="err" style={{ padding: "8px 24px" }}>Could not load community areas: {areas.error}</p>}
      <MapScreen areas={areas.ok ? areas.value : []} initial={sp} bounds={region.bounds ?? undefined} regionName={region.name} />
    </>
  );
}
