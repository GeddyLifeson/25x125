import Link from "next/link";
import { notFound } from "next/navigation";
import { Source } from "../../../components/Source";
import { getAreaSnapshot, getLots, settle } from "../../../lib/engine";
import { day, num, titleCase, usd } from "../../../lib/format";
import { SCORE_LABEL } from "../../../lib/labels";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ num: string }> };

export async function generateMetadata({ params }: Props) {
  const { num: n } = await params;
  const r = /^\d{1,2}$/.test(n) ? await settle(getAreaSnapshot(n)) : null;
  return { title: r?.ok ? `${r.value.name}: lots, sales and costs · 25x125` : "Community area · 25x125" };
}

export default async function AreaPage({ params }: Props) {
  const { num: n } = await params;
  if (!/^\d{1,2}$/.test(n)) notFound();
  const snapR = await settle(getAreaSnapshot(n));
  if (!snapR.ok) {
    if (snapR.status === 404) notFound();
    return (
      <main className="wrap">
        <p className="err">Could not load this area: {snapR.error}</p>
      </main>
    );
  }
  const a = snapR.value;
  const [topR, taxR] = await Promise.all([
    settle(getLots(`community_area=${a.num}&sort=score&limit=15`)),
    settle(getLots(`community_area=${a.num}&tax_sale=true&sort=score&limit=10`)),
  ]);
  const top = topR.ok ? topR.value : [];
  const tax = taxR.ok ? taxR.value : [];
  const building = a.sales.find((s) => s.kind === "building");
  const condo = a.sales.find((s) => s.kind === "condo");

  return (
    <main className="wrap">
      <section className="head">
        <div>
          <Link href="/areas" style={{ fontSize: 13 }}>
            All community areas
          </Link>
          <h1>{a.name}</h1>
          <span className="muted">Community area {a.num} · Chicago</span>
        </div>
        <div className="btns">
          <Link className="btn primary" href={`/?community_area=${a.num}`}>
            Search lots in {a.name}
          </Link>
        </div>
      </section>

      <section aria-label="Area facts" className="facts">
        <div className="fact">
          <span className="l">New building sale, per unit</span>
          <span className="v">{building ? usd(building.median_per_unit) : "n/a"}</span>
          <span className="n">
            {building ? `Median of ${building.sales} sales, ${day(building.first_sale)} to ${day(building.last_sale)}` : "No whole-building sales in 3 years"}{" "}
            <Source>{a.sales_source}</Source>
          </span>
        </div>
        <div className="fact">
          <span className="l">New condo unit sale</span>
          <span className="v">{condo ? usd(condo.median_per_unit) : "n/a"}</span>
          <span className="n">
            {condo ? `Median of ${condo.sales} sales, ${day(condo.first_sale)} to ${day(condo.last_sale)}` : "No new condo sales in 3 years"}{" "}
            <Source>{a.sales_source}</Source>
          </span>
        </div>
        <div className="fact">
          <span className="l">Construction cost index</span>
          <span className="v">{a.cost_index ? a.cost_index.index.toFixed(2) : "n/a"}</span>
          <span className="n">
            {a.cost_index
              ? `City median is 1.00 · ${a.cost_index.permits} permits${a.cost_index.thin ? " · thin, blended with neighboring areas" : ""}`
              : "No permits on file"}{" "}
            {a.cost_index && <Source>{`${a.cost_index.source}; computed ${a.cost_index.computed_on}`}</Source>}
          </span>
        </div>
        <div className="fact">
          <span className="l">Land, per lot sq ft</span>
          <span className="v">{a.land_value ? usd(a.land_value.per_lot_sqft) : "n/a"}</span>
          <span className="n">
            {a.land_value
              ? `Median of ${a.land_value.sales} vacant and teardown sales${a.land_value.sales < 5 ? " (thin: fewer than 5)" : ""}`
              : "No land sales in 36 months"}{" "}
            {a.land_value && <Source>{`${a.land_value.source}; sales ${a.land_value.first_sale} to ${a.land_value.last_sale}; computed ${a.land_value.computed_on}`}</Source>}
          </span>
        </div>
      </section>

      <section className="card">
        <h2>Top-scored lots</h2>
        <p className="sub">
          The 15 highest development scores in {a.name}. {SCORE_LABEL}
        </p>
        {top.length === 0 ? (
          <p className="muted">No scored lots in this area.</p>
        ) : (
          <LotTable lots={top} />
        )}
      </section>

      <section className="card">
        <h2>Lots in the next county tax sale</h2>
        <p className="sub">
          Listed by the Cook County Treasurer for the Annual Tax Sale. Owners can pay until the sale, which takes the lot off the list.
        </p>
        {tax.length === 0 ? (
          <p className="muted">No lots in {a.name} are on the current list.</p>
        ) : (
          <>
            <LotTable lots={tax} tax />
            <p className="small" style={{ marginTop: 10 }}>
              <Link href={`/?community_area=${a.num}&tax_sale=true`}>See all on the map</Link>
            </p>
          </>
        )}
      </section>

      <p className="small muted">Estimates, not tax, legal, zoning or appraisal advice.</p>
    </main>
  );
}

function LotTable({ lots, tax }: { lots: import("../../../lib/types").Lot[]; tax?: boolean }) {
  return (
    <div className="scroll">
      <table className="t">
        <thead>
          <tr>
            <th>Address</th>
            <th>Zoning</th>
            <th className="num">Lot</th>
            <th className="num">Units by right</th>
            <th className="num">Score</th>
            {tax && <th className="num">Due at tax sale</th>}
          </tr>
        </thead>
        <tbody>
          {lots.map((l) => (
            <tr key={l.pin10}>
              <td>
                <Link href={`/parcels/${l.pin}`}>{titleCase(l.address) || `Lot ${l.pin10}`}</Link>
              </td>
              <td>{l.zone_class ?? "n/a"}</td>
              <td className="num">{l.lot_sqft ? `${num(l.lot_sqft)} sq ft` : "n/a"}</td>
              <td className="num">{l.by_right_units ?? 0}</td>
              <td className="num">{num(l.score)}</td>
              {tax && <td className="num">{usd(l.tax_sale_due)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
