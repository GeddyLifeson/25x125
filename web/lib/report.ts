// Shared pieces for the feasibility screen, the CSV export and the PDF: where each number comes from.
import { csvCell } from "./overrides";
import type { Feasibility, Scenario } from "./types";

export const ESTIMATE_LABEL = "Estimates, not tax, legal, zoning or appraisal advice.";

export type SourceRow = { what: string; source: string; asOf: string };

/** Each input of a scenario with its source and date (CLAUDE.md rule 2). */
export function scenarioSources(f: Feasibility, s: Scenario): SourceRow[] {
  const rows: SourceRow[] = [];
  const ci = f.inputs.cost_index;
  if (ci)
    rows.push({
      what: `Area cost index ${ci.index.toFixed(2)}`,
      source: `Chicago building permits (ydr8-5enu), ${ci.permits} new 2-6 unit permits${ci.thin ? `, blended with neighboring areas (weight ${ci.neighbor_weight.toFixed(2)})` : ""}`,
      asOf: `computed ${ci.computed_on}`,
    });
  const lv = f.inputs.land_value;
  if (lv)
    rows.push({
      what: "Land value map",
      source: `${lv.sales} vacant and teardown sales (${lv.geo} ${lv.geo_id}), Cook County Assessor sales`,
      asOf: `sales ${lv.first_sale} to ${lv.last_sale}`,
    });
  const esc = f.inputs.escalation;
  if (esc)
    rows.push({
      what: `Cost escalation x${esc.factor.toFixed(4)}`,
      source: esc.basis,
      asOf: `index month ${esc.latest_month.slice(0, 7)}`,
    });
  rows.push({
    what: `Build-spec preset (${s.cost.preset}) $${s.cost.base_per_sqft} per sq ft`,
    source: "data/rules/feasibility_defaults.json, from docs/construction-costs-2026-10-29.md",
    asOf: "set 2026-10-29",
  });
  if (s.sale_source)
    rows.push({
      what: `Sale price per unit, ${s.sale_source.comps} comps within ${s.sale_source.radius_mi} mi`,
      source: s.sale_source.source + (s.sale_source.notes.length ? ` (${s.sale_source.notes.join("; ")})` : ""),
      asOf: "comps from the last 3 years, adjusted to today",
    });
  if (s.rent_source)
    rows.push({
      what: "Rent per unit",
      source: `U.S. Census Bureau ACS 5-year, ${s.rent_source.acs_source}; x${s.rent_source.growth_since_acs.toFixed(3)} rent growth since the survey; x${s.rent_source.factor} new-building factor`,
      asOf: "ACS 2020-2024",
    });
  for (const c of s.path.citations)
    rows.push({ what: `Zoning: ${s.path.district} (${s.path.id.replace(/_/g, " ")})`, source: c, asOf: (c.match(/verified (\d{4}-\d{2}-\d{2})/) ?? [])[1] ?? "see citation" });
  return rows;
}

function rowsForScenario(f: Feasibility, s: Scenario, letter: string): unknown[][] {
  const r: unknown[][] = [];
  const add = (section: string, item: string, basis: string, value: unknown, low?: unknown, high?: unknown) =>
    r.push([letter, s.name, section, item, basis, value, low ?? "", high ?? ""]);
  add("scenario", "Units", s.approval, s.units);
  add("scenario", "Gross floor area (sq ft)", "", s.gross_sqft);
  add("scenario", "Unit size (sq ft)", "", s.unit_sqft);
  for (const l of s.lines) add("cost", l.name, l.basis, Math.round(l.value), Math.round(l.low), Math.round(l.high));
  add("cost", "Total cost", s.cost_range.label, s.cost_range.central, s.cost_range.low, s.cost_range.high);
  add("cost", "Total cost per unit", "", s.cost_per_unit);
  if (s.sell) {
    const x = s.sell;
    add("sell", "Sale value", `${x.sale_per_unit} per unit`, x.sale_total, x.sale_range?.low, x.sale_range?.high);
    add("sell", "Net sale", x.net_sale_basis, x.net_sale);
    add("sell", "Profit", "net sale - total cost", x.profit);
    add("sell", "Return on cost", "profit / total cost", x.return_on_cost);
    add("sell", "Margin on net sale", "profit / net sale", x.margin_on_net_sale);
    for (const [k, v] of Object.entries(x.max_land_price_at))
      add("sell", `Max land price at ${k} return on cost`, x.reference_lines.label, v);
    if (x.range) {
      add("sell", "Profit P10", x.range.label, x.range.p10);
      add("sell", "Profit P25", x.range.label, x.range.p25);
      add("sell", "Profit P50", x.range.label, x.range.p50);
      add("sell", "Profit P90", x.range.label, x.range.p90);
      add("sell", "Share of draws with a loss", x.range.label, x.range.loss_share);
    }
    if (x.stress_case) add("sell", "Stress case profit", x.stress_case.label, x.stress_case.profit);
  }
  if (s.hold) {
    const h = s.hold;
    add("hold", "Rent per unit per month", "", h.rent_per_unit, h.rent_range?.low, h.rent_range?.high);
    add("hold", "Effective gross income", "rent x 12 x units x 0.95 vacancy", h.effective_gross_income);
    add("hold", "Operating costs before tax", "", h.operating_costs_before_tax);
    add("hold", "Property tax", "", h.property_tax);
    add("hold", "Net operating income", "", h.noi);
    add("hold", "Value", h.value_basis, h.value);
    add("hold", "Yield on cost", "NOI / total cost", h.yield_on_cost);
    add("hold", "Spread over cap rate (points)", h.reference_lines.label, h.spread_over_cap_rate_pts);
    add("hold", "Equity created", "value - total cost", h.equity_created);
    add("hold", "Loan at DSCR", h.loan_at_dscr_basis, h.loan_at_dscr);
    add("hold", "Refinance gap", "construction loan (65% of total cost) - loan at DSCR", h.refinance_gap);
  }
  for (const i of s.incentives)
    add("incentive", i.name, `${i.on ? "on" : "off"}; ${i.kind}; ${i.basis}${i.note ? `; ${i.note}` : ""}${i.applies ? "" : "; does not apply to this parcel or exit"}`, i.on ? i.value : 0);
  for (const fl of s.flags) add("flag", fl.tag, fl.text, "");
  for (const src of scenarioSources(f, s)) add("source", src.what, src.source, src.asOf);
  return r;
}

export function feasibilityCsv(f: Feasibility, address: string, generatedOn: string): string {
  const head = ["scenario", "scenario_name", "section", "item", "basis", "value", "low", "high"];
  const rows: unknown[][] = [
    ["#", `25x125 feasibility, ${address}, PIN ${f.pin}, exit: ${f.exit}, generated ${generatedOn}`],
    ["#", ESTIMATE_LABEL],
    head,
  ];
  f.scenarios.forEach((s, i) => rows.push(...rowsForScenario(f, s, "ABC"[i])));
  for (const z of f.zoning_flags) rows.push(["all", "", "zoning flag", z.id, `${z.text} (${z.citation ?? ""})`, z.dollars ?? ""]);
  return rows.map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";
}
