import Link from "next/link";
import { notFound } from "next/navigation";
import { SaveDeal } from "../../../components/SaveDeal";
import { Source } from "../../../components/Source";
import { getParcel, getSaleValue, getZoning, postFeasibility, settle } from "../../../lib/engine";
import { day, feet, formatPin, num, pct, sqft, titleCase, usd } from "../../../lib/format";
import type { Feasibility, Incentive, Parcel } from "../../../lib/types";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ pin: string }>; searchParams: Promise<{ target?: string }> };

const USE_NOW: Record<string, string> = { vacant: "Vacant lot", multi: "Multi-unit building", single: "House", mixed: "Mixed use" };
const SIGNAL_NAMES: Record<string, string> = {
  violation: "Building violation",
  vacant_building_311: "311 report: vacant building",
  vacant_lot_311: "311 report: vacant lot",
  demolition_notice: "Demolition notice",
  scofflaw: "Building scofflaw list",
  city_owned: "City-owned land record",
  hearing_fine: "Administrative hearing fine",
  environmental_hold: "Environmental hold",
  foreclosed_rental: "Foreclosed rental registration",
  foreclosure_auction: "Foreclosure auction",
  rezoning: "Rezoning application",
};

function Fact({ label, value, note, src }: { label: string; value: string; note: string; src: React.ReactNode }) {
  return (
    <div className="fact">
      <span className="l">{label}</span>
      <span className="v">{value}</span>
      <span className="n">
        {note} <Source>{src}</Source>
      </span>
    </div>
  );
}

function rezoneTargets(notes: string[]): string[] {
  const n = notes.find((x) => x.startsWith("other targets:"));
  return n ? n.replace("other targets:", "").split(",").map((s) => s.trim()).filter(Boolean) : [];
}

function checks(p: Parcel, f: Feasibility | null): string[] {
  const out: string[] = [];
  if (p.environmental_hold) out.push(`Environmental hold on file: ${p.environmental_hold}`);
  if (p.demolition_notice_date) out.push(`Demolition notice dated ${day(p.demolition_notice_date)}`);
  if (p.open_violations) out.push(`${p.open_violations} open building violation(s); last ${day(p.last_violation_date)}`);
  if (p.vacant_building_fine_due) out.push(`Vacant building fines due: ${usd(p.vacant_building_fine_due)}`);
  if (p.hearing_fines_3y) out.push(`Administrative hearing fines in 3 years: ${usd(p.hearing_fines_3y)}`);
  if (p.scofflaw) out.push("Owner is on the city's building scofflaw list");
  if (p.city_owned_status) out.push(`City-owned land record: ${p.city_owned_status}`);
  if (p.landmark_name || p.historic_rating)
    out.push(`Historic status: ${[p.landmark_name, p.historic_rating].filter(Boolean).join(", ")}; demolition may be delayed`);
  if (p.exempt_owner) out.push(`Tax-exempt owner of record: ${p.exempt_owner}`);
  if (p.aro_area) out.push(`${p.aro_area}: affordable units apply at 10 or more units`);
  for (const z of f?.zoning_flags ?? []) out.push(z.text);
  if (p.zone_class_2) out.push(`Lot is split between ${p.zone_class} (${pct(p.zone_share, 0)}) and ${p.zone_class_2} (${pct(p.zone_share_2, 0)})`);
  out.push("Not in our data: soil report, water service tap size, alley access, title and survey");
  return out;
}

export default async function ParcelPage({ params, searchParams }: Props) {
  const { pin } = await params;
  const { target } = await searchParams;
  const parcelR = await settle(getParcel(pin));
  if (!parcelR.ok) {
    if (parcelR.status === 404 || parcelR.status === 400) notFound();
    return (
      <main className="wrap">
        <p className="err">Could not load this parcel: {parcelR.error}</p>
      </main>
    );
  }
  const p = parcelR.value;
  const zoningR = await settle(getZoning(p.pin, target));
  const z = zoningR.ok ? zoningR.value : null;
  const byRight = z?.paths.find((x) => x.id === "by_right") ?? z?.paths[0];
  // Comps for the by-right unit count, 2 to 6 units (the comp pool's range).
  const priceUnits = Math.min(6, Math.max(2, byRight?.units ?? 3));
  const [sellR, holdR, saleR] = await Promise.all([
    settle(postFeasibility(p.pin, "sell", target, {})),
    settle(postFeasibility(p.pin, "hold", target, {})),
    settle(getSaleValue(p.pin, priceUnits)),
  ]);
  const fs = sellR.ok ? sellR.value : null;
  const fh = holdR.ok ? holdR.value : null;
  const sv = saleR.ok ? saleR.value : null;
  const pulled = day(p.pulled_at);
  const a = fs?.scenarios[0];
  const lv = fs?.inputs.land_value;
  const rezPath = z?.paths.find((x) => x.id === "rezoning");
  const targets = rezPath ? [rezPath.district, ...rezoneTargets(rezPath.notes)] : [];
  const compDates = sv?.comp_list.map((c) => c.sale_date).sort() ?? [];
  const lastSale = p.recent_sales[0];

  // Incentives at maximum value across the two exits (CLAUDE.md rule 6).
  const inc = new Map<string, { i: Incentive; exit: string }>();
  for (const [f, exit] of [
    [fs, "sell"],
    [fh, "hold"],
  ] as const) {
    for (const s of f?.scenarios ?? [])
      for (const i of s.incentives) {
        const cur = inc.get(i.id);
        if (!cur || (i.applies && (!cur.i.applies || i.value > cur.i.value))) inc.set(i.id, { i, exit });
      }
  }
  const incList = [...inc.values()].sort((x, y) => Number(y.i.applies) - Number(x.i.applies) || y.i.value - x.i.value);

  const overlays: { name: string; value: string; good?: boolean; src: string }[] = [
    {
      name: "Transit-served location",
      value: p.transit_served ?? "No",
      good: !!p.transit_served,
      src: `CTA rail ${feet(p.cta_rail_ft)}, Metra ${feet(p.metra_ft)}. Chicago GIS transit-served buffers (Zoning MapServer 13, 14, 24), CTA stations (8pix-ypme), Metra GTFS; pulled ${pulled}`,
    },
    { name: "TIF district", value: p.tif_name ?? "No", src: `City of Chicago TIF districts (eejr-xtfb); pulled ${pulled}` },
    {
      name: "Opportunity Zone (2018 map)",
      value: p.opportunity_zone_2018 ? "Yes" : "No",
      good: !!p.opportunity_zone_2018,
      src: `2018 Treasury Opportunity Zone list (US DOT copy, 181 Cook tracts), valid through 2028; tract ${p.tract ?? "n/a"}; pulled ${pulled}`,
    },
    {
      name: "Enterprise Zone",
      value: p.enterprise_zone ? `Zone ${p.enterprise_zone}` : "No",
      good: !!p.enterprise_zone,
      src: `Chicago GIS Enterprise Zones (operational MapServer 73); pulled ${pulled}`,
    },
    {
      name: "Historic rating",
      value: [p.landmark_name, p.historic_rating].filter(Boolean).join(", ") || "None",
      src: `Chicago historic survey (2u8t-236p) and landmarks (uct4-hrvh); pulled ${pulled}`,
    },
    { name: "Special district", value: p.special_district ?? "None", src: `Chicago GIS zoning special districts (Zoning MapServer 9); pulled ${pulled}` },
    { name: "Affordable housing (ARO) area", value: p.aro_area ?? "None", src: `Chicago GIS ARO areas (Zoning MapServer 20); pulled ${pulled}` },
    { name: "ADU zone", value: p.adu_zone ?? "Not in an ADU zone", src: `Chicago GIS ADU areas (Zoning MapServer 17); pulled ${pulled}` },
    { name: "Pedestrian street", value: p.pedestrian_street ?? "No", src: `Chicago GIS pedestrian streets (Zoning MapServer 4); pulled ${pulled}` },
    {
      name: "Inside fire limits",
      value: p.fire_limits ? "Yes · masonry required" : "No · wood frame OK",
      good: !p.fire_limits,
      src: `Municipal Code 13-116-010, traced to data/rules/fire_limits.geojson; verified 2026-10-30`,
    },
  ];

  const history: { date: string; text: string }[] = [
    ...p.signals.map((s) => ({
      date: s.date ? s.date.slice(0, 7) : "no date",
      text: `${SIGNAL_NAMES[s.kind] ?? s.kind}${s.status ? ` (${s.status.toLowerCase()})` : ""}${s.detail ? `: ${s.detail}` : ""}`,
    })),
    ...p.recent_sales.map((s) => ({
      date: s.date.slice(0, 7),
      text: `Sold for ${usd(s.price)}${s.deed_type ? ` (${s.deed_type.toLowerCase()} deed)` : ""}`,
    })),
  ].sort((x, y) => (y.date > x.date ? 1 : -1));

  const address = titleCase(p.address) || `PIN ${formatPin(p.pin)}`;
  const tq = target ? `?target=${encodeURIComponent(target)}` : "";

  return (
    <main className="wrap">
      <section className="head">
        <div>
          <Link href="/" style={{ fontSize: 13 }}>
            Back to search
          </Link>
          <h1>{address}</h1>
          <span className="muted">
            {titleCase(p.community_area)} · Ward {p.ward ?? "n/a"} · PIN {formatPin(p.pin)} · ZIP {p.zip ?? "n/a"} · Assessor
            neighborhood {p.nbhd_code ?? "n/a"}
          </span>
        </div>
        <div className="btns">
          <SaveDeal pin={p.pin} />
          <Link className="btn primary" href={`/parcels/${p.pin}/feasibility${tq}`}>
            Run feasibility
          </Link>
        </div>
      </section>

      <section aria-label="Key facts" className="facts">
        <Fact
          label="Zoning"
          value={p.zone_class ?? "n/a"}
          note={p.zone_class_2 ? `${pct(p.zone_share, 0)} of lot; ${p.zone_class_2} on the rest` : "Whole lot"}
          src={`${p.sources.zoning}; pulled ${pulled}`}
        />
        <Fact
          label="Lot"
          value={p.frontage_ft && p.depth_ft ? `${num(p.frontage_ft)} x ${num(p.depth_ft)}` : sqft(p.lot_sqft)}
          note={`${sqft(p.lot_sqft)} · Assessor class ${p.class ?? "n/a"}`}
          src={`${p.sources.parcel}, tax year ${p.tax_year}; lot from ${p.lot_source ?? "n/a"}; pulled ${pulled}`}
        />
        <Fact
          label="On the lot now"
          value={p.use_now ? (USE_NOW[p.use_now] ?? titleCase(p.use_now)) : "n/a"}
          note={`${p.units_now ?? 0} unit(s)${p.stories ? ` · ${p.stories} stories` : ""}`}
          src={`Cook County Assessor building characteristics, summed over building cards; pulled ${pulled}`}
        />
        <Fact
          label="Buildable by right"
          value={byRight ? `${byRight.units} unit${byRight.units === 1 ? "" : "s"}` : "n/a"}
          note={byRight ? `${sqft(byRight.floor_area_sqft)} · ${num(byRight.max_height_ft)} ft` : (zoningR.ok ? "" : zoningR.error)}
          src={byRight ? byRight.citations.join(" | ") : "Zoning rules not available"}
        />
        <Fact
          label={`New ${priceUnits}-unit sale, per unit`}
          value={sv ? usd(sv.per_unit) : "n/a"}
          note={sv ? `${sv.comps} comps within ${sv.radius_mi} mi` : saleR.ok ? "" : saleR.error}
          src={
            sv
              ? `${sv.source}. 80% range ${usd(sv.low)} to ${usd(sv.high)} (${sv.range}). Sales ${day(compDates[0])} to ${day(compDates[compDates.length - 1])}, adjusted to today. ${sv.label}.`
              : "No comps"
          }
        />
        <Fact
          label="Land value"
          value={lv?.per_buildable_sqft ? `${usd(lv.per_buildable_sqft)} / sq ft` : lv ? `${usd(lv.per_lot_sqft)} / lot sq ft` : "n/a"}
          note={lv ? `per buildable sq ft · ${lv.sales} land sales` : "No land sales nearby"}
          src={lv ? `${lv.source}; ${lv.geo} ${lv.geo_id}; ${usd(lv.per_lot_sqft)} per lot sq ft; sales ${lv.first_sale} to ${lv.last_sale}` : "Land value map"}
        />
        <Fact
          label="Max land price, scenario A"
          value={a?.sell ? usd(a.sell.max_land_price) : "n/a"}
          note={a?.sell ? `At ${pct(a.sell.target_return_on_cost, 0)} return on cost, ${a.units} units` : ""}
          src={
            a?.sell
              ? `Residual land value from the feasibility engine: ${Object.entries(a.sell.max_land_price_at)
                  .map(([k, v]) => `${usd(v)} at ${k}`)
                  .join(", ")}. ${a.sell.reference_lines.label}. Sale ${usd(a.sell.sale_per_unit)} per unit from comps; costs from the cost index computed ${fs?.inputs.cost_index?.computed_on ?? "n/a"}.`
              : "Feasibility not available"
          }
        />
        <Fact
          label="Last recorded sale"
          value={lastSale ? usd(lastSale.price) : "None on file"}
          note={lastSale ? `${lastSale.date}${lastSale.deed_type ? ` · ${lastSale.deed_type.toLowerCase()} deed` : ""}` : "No sale in the Assessor file"}
          src={`Cook County Assessor parcel sales (wvhk-k5uv); pulled ${pulled}`}
        />
      </section>

      <div className="cols">
        <div className="main">
          <section className="card">
            <h2>What zoning allows</h2>
            <p className="sub">
              {z?.zone_class ?? p.zone_class} · {sqft(z?.lot_sqft ?? p.lot_sqft)} lot · Chicago Zoning Ordinance, rules
              verified 2026-10-30
              {targets.length > 1 && (
                <>
                  {" "}
                  · Rezoning target:{" "}
                  {targets.map((t, i) => (
                    <span key={t}>
                      {i > 0 && " | "}
                      {t === (target ?? targets[0]) ? <b>{t}</b> : <Link href={`?target=${encodeURIComponent(t)}`}>{t}</Link>}
                    </span>
                  ))}
                </>
              )}
            </p>
            {z ? (
              <div className="scroll">
                <table className="t">
                  <thead>
                    <tr>
                      <th>Path</th>
                      <th className="num">Units</th>
                      <th className="num">Floor area</th>
                      <th className="num">Height</th>
                      <th className="num">Parking</th>
                      <th>Approval</th>
                    </tr>
                  </thead>
                  <tbody>
                    {z.paths.map((x) => (
                      <tr key={x.id}>
                        <td>
                          <b style={{ fontWeight: 500 }}>{x.name}</b>
                          <div className="basis">
                            {x.district}
                            {x.notes.length > 0 && ` · ${x.notes.join("; ")}`}{" "}
                            <Source label="rule">
                              {x.citations.map((c) => (
                                <span key={c} style={{ display: "block" }}>
                                  {c}
                                </span>
                              ))}
                            </Source>
                          </div>
                        </td>
                        <td className="num">{x.units}</td>
                        <td className="num">{sqft(x.floor_area_sqft)}</td>
                        <td className="num">{x.max_height_ft ? `${num(x.max_height_ft)} ft` : "n/a"}</td>
                        <td className="num">{x.parking_spaces ?? "n/a"}</td>
                        <td>{x.approval}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="err">Zoning not available: {zoningR.ok ? "" : zoningR.error}</p>
            )}
            {z && z.flags.length > 0 && (
              <ul className="plain flags" style={{ marginTop: 12 }}>
                {z.flags.map((f) => (
                  <li key={f.id}>
                    <span className="tag c">Cost</span>
                    <span>
                      {f.text} {f.citation && <Source label="rule">{f.citation}</Source>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {!z?.covered && z && <p className="err" style={{ marginTop: 10 }}>This district is not covered by the rules yet; check the result by hand.</p>}
          </section>

          <section className="card">
            <h2>Nearby comparables</h2>
            <p className="sub">
              {sv
                ? `New-construction first sales, ${sv.same_size_group ? `same size group (${priceUnits} units)` : "any unit count"}, within ${sv.radius_mi} mi · ${sv.comps} sales from ${day(compDates[0])} to ${day(compDates[compDates.length - 1])} · top ${sv.comp_list.length} by weight shown`
                : "No comparable sales found."}
            </p>
            {sv && (
              <div className="scroll">
                <table className="t">
                  <thead>
                    <tr>
                      <th>PIN</th>
                      <th>Type</th>
                      <th>Sold</th>
                      <th className="num">Price per unit</th>
                      <th className="num">Adjusted to today</th>
                      <th className="num">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sv.comp_list.slice(0, 12).map((c) => (
                      <tr key={c.pin + c.sale_date}>
                        <td className="mono">
                          <Link href={`/parcels/${c.pin}`}>{formatPin(c.pin)}</Link>
                        </td>
                        <td>{c.kind === "condo" ? "Condo unit" : "Whole building"}</td>
                        <td>{c.sale_date}</td>
                        <td className="num">{usd(c.price_per_unit)}</td>
                        <td className="num">{usd(c.adjusted)}</td>
                        <td className="num">{c.weight.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {sv && (
              <p className="small muted" style={{ marginTop: 10 }}>
                Estimate {usd(sv.per_unit)} per unit, 80% range {usd(sv.low)} to {usd(sv.high)}. Adjusted prices use the
                FHFA metro index and a 0.70 factor on condo comps for whole-building estimates. {sv.notes.join(" ")}{" "}
                <Source>{sv.source}. {sv.label}.</Source>
              </p>
            )}
          </section>

          <section className="card">
            <h2>Violation, 311 and sale history</h2>
            <p className="sub">
              Last 25 records matched to this lot <Source>{p.sources.signals}; Cook County Assessor sales; pulled {pulled}</Source>
            </p>
            {history.length === 0 ? (
              <p className="muted">No violations, 311 reports, demolition notices, city land records or sales on file.</p>
            ) : (
              <ul className="plain hist">
                {history.map((h, i) => (
                  <li key={i}>
                    <span>{h.date}</span>
                    <span>{h.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="side">
          <section className="card">
            <h2 style={{ marginBottom: 14 }}>Overlays</h2>
            <ul className="plain">
              {overlays.map((o) => (
                <li key={o.name}>
                  <span>
                    {o.name} <Source>{o.src}</Source>
                  </span>
                  <span className={o.good ? "good right" : "muted right"}>{o.value}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2>Incentives that may apply</h2>
            <p className="sub small">Maximum values, scenario by scenario. Toggle what applies on the feasibility screen.</p>
            <ul className="plain">
              {incList.map(({ i, exit }) => (
                <li key={i.id}>
                  <span>
                    {i.name} <Source>{`${i.basis}${i.note ? `. ${i.note}` : ""}. Rules in data/rules/incentives_v1.csv.`}</Source>
                  </span>
                  <span className="mono right" style={{ fontWeight: 500 }}>
                    {!i.applies ? "Not matched" : i.kind === "flag" ? "Flag" : `${usd(i.value)}${exit === "hold" ? " (hold)" : ""}`}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card warn">
            <h2 style={{ marginBottom: 10 }}>Check before buying</h2>
            <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
              {checks(p, fs).map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </section>

          <p className="small muted">
            {fs?.label ?? "Estimates, not tax, legal, zoning or appraisal advice."} Parcel data pulled {pulled}.
          </p>
        </aside>
      </div>
    </main>
  );
}
