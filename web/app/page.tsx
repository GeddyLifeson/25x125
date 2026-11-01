import Link from "next/link";
import { redirect } from "next/navigation";
import { ENGINE_URL, searchParcels, settle } from "../lib/engine";
import { formatPin, num, titleCase } from "../lib/format";

export const dynamic = "force-dynamic";

async function engineStatus(): Promise<string | null> {
  try {
    const res = await fetch(`${ENGINE_URL}/health`, { cache: "no-store" });
    const body = (await res.json()) as { status: string };
    return body.status === "ok" || body.status === "stale" ? null : `The engine reports: ${body.status}.`;
  } catch {
    return `The engine is not answering at ${ENGINE_URL}. Start it with: python -m uvicorn engine.app:app --port 8000`;
  }
}

export default async function Home({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q: rawQ } = await searchParams;
  const q = (rawQ ?? "").trim();
  const status = await engineStatus();
  const result = q.length >= 3 ? await settle(searchParcels(q)) : null;
  if (result?.ok && result.value.length === 1) redirect(`/parcels/${result.value[0].pin}`);

  return (
    <main className="wrap">
      <section className="card">
        <h1 style={{ fontSize: 24, marginBottom: 6 }}>Find a Chicago parcel</h1>
        <p className="muted" style={{ marginBottom: 14 }}>
          Type a street address (for example 624 N Troy St) or a 10- or 14-digit PIN. Results come from the Cook County
          Assessor address file, copied nightly.
        </p>
        <form className="search" action="/" method="get" role="search">
          <input
            name="q"
            defaultValue={q}
            placeholder="Address or PIN"
            aria-label="Address or PIN"
            autoComplete="off"
            minLength={3}
            autoFocus
          />
          <button className="btn primary" type="submit">
            Search
          </button>
        </form>
        {status && <p className="err" style={{ marginTop: 10 }}>{status}</p>}
      </section>

      {q.length > 0 && q.length < 3 && <p className="muted">Type at least 3 characters.</p>}

      {result && !result.ok && <p className="err">Search failed: {result.error}</p>}

      {result?.ok && (
        <section className="card">
          <h2>
            {result.value.length === 0
              ? `No parcels match "${q}"`
              : `${result.value.length}${result.value.length === 25 ? "+" : ""} parcels match "${q}"`}
          </h2>
          <p className="sub">Addresses in street order. A building with condo units lists one row per unit PIN.</p>
          {result.value.length > 0 && (
            <div className="scroll">
              <table className="t hits">
                <thead>
                  <tr>
                    <th>Address</th>
                    <th>PIN</th>
                    <th>ZIP</th>
                    <th>Zoning</th>
                    <th className="num">Lot</th>
                  </tr>
                </thead>
                <tbody>
                  {result.value.map((h) => (
                    <tr key={h.pin}>
                      <td>
                        <Link href={`/parcels/${h.pin}`}>
                          <span className="addr">{titleCase(h.address) || "No address on file"}</span>
                        </Link>
                      </td>
                      <td className="mono">{formatPin(h.pin)}</td>
                      <td>{h.zip ?? ""}</td>
                      <td>{h.zone_class ?? "n/a"}</td>
                      <td className="num">{h.lot_sqft ? `${num(h.lot_sqft)} sq ft` : "n/a"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
