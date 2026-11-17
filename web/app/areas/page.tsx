import Link from "next/link";
import { getCommunityAreas, settle } from "../../lib/engine";

export const dynamic = "force-dynamic";
export const metadata = { title: "Chicago community areas · 25x125" };

export default async function AreasPage() {
  const r = await settle(getCommunityAreas());
  if (!r.ok)
    return (
      <main className="wrap">
        <p className="err">Could not load community areas: {r.error}</p>
      </main>
    );
  const areas = [...r.value].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <main className="wrap">
      <section className="head">
        <div>
          <h1>Chicago community areas</h1>
          <span className="muted">
            {areas.length} areas. Each page shows new-construction sales, the construction cost index, land value and the top-scored lots.
          </span>
        </div>
      </section>
      <section className="card">
        <ul className="arealist" data-testid="areas">
          {areas.map((a) => (
            <li key={a.num}>
              <Link href={`/areas/${a.num}`}>{a.name}</Link> <span className="muted small">{a.num}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
