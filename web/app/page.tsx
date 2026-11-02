import { redirect } from "next/navigation";
import MapPage from "./map/page";

export const dynamic = "force-dynamic";
export const metadata = { title: "25x125 search" };

// The opening screen is Search (mockups/Main.dc.html): filters, the ranked list and the map.
// Old address-search links (/?q=...) go to /search.
export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  if (sp.q) redirect(`/search?q=${encodeURIComponent(sp.q)}`);
  return MapPage({ searchParams: Promise.resolve(sp) });
}
