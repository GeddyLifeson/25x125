import { getDeals, settle } from "../../lib/engine";
import { DealsScreen } from "./DealsScreen";

export const dynamic = "force-dynamic";
export const metadata = { title: "25x125 deals" };

export default async function DealsPage({ searchParams }: { searchParams: Promise<{ d?: string }> }) {
  const { d } = await searchParams;
  const deals = await settle(getDeals());
  if (!deals.ok) {
    return (
      <main className="wrap">
        <h1>Deals</h1>
        <p className="err">Could not load deals: {deals.error}</p>
      </main>
    );
  }
  const pick = d && /^\d+$/.test(d) ? Number(d) : null;
  return <DealsScreen initial={deals.value} initialPick={pick} />;
}
