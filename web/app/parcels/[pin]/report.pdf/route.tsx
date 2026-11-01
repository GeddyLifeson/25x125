// One-page PDF of the feasibility result, for a partner or lender. Pure JavaScript (no browser needed to deploy).
import { Document, Page, StyleSheet, Text, View, renderToBuffer } from "@react-pdf/renderer";
import { EngineError, checkExport, getParcel, postFeasibility, wallRedirect } from "../../../../lib/engine";
import { formatPin, pct, titleCase, usd, usdRange } from "../../../../lib/format";
import { overridesFromParam, overridesToCsv } from "../../../../lib/overrides";
import { ESTIMATE_LABEL, scenarioSources } from "../../../../lib/report";
import type { Feasibility, Overrides, Parcel } from "../../../../lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ink = "#16191D";
const muted = "#5A6169";
const line = "#DDE1E5";
const s = StyleSheet.create({
  page: { padding: 26, fontSize: 7.4, fontFamily: "Helvetica", color: ink, lineHeight: 1.3 },
  brand: { fontFamily: "Courier-Bold", fontSize: 11 },
  h1: { fontSize: 14, fontFamily: "Helvetica-Bold", marginTop: 4 },
  h2: { fontSize: 9, fontFamily: "Helvetica-Bold", marginTop: 8, marginBottom: 3 },
  muted: { color: muted },
  row: { flexDirection: "row", borderBottomWidth: 0.5, borderBottomColor: line, paddingVertical: 1.5 },
  head: { flexDirection: "row", borderBottomWidth: 0.8, borderBottomColor: ink, paddingVertical: 2, fontFamily: "Helvetica-Bold" },
  cols: { flexDirection: "row", gap: 14 },
  label: { marginTop: 8, padding: 6, backgroundColor: "#FFF7EF", borderWidth: 0.5, borderColor: "#F1D3B4" },
});

function Cell({ w, right, bold, children }: { w: number | string; right?: boolean; bold?: boolean; children: React.ReactNode }) {
  return (
    <Text style={{ width: w, textAlign: right ? "right" : "left", fontFamily: bold ? "Helvetica-Bold" : "Helvetica", paddingRight: 4 }}>
      {children}
    </Text>
  );
}

function Report({ f, p, pick, overrides, today }: { f: Feasibility; p: Parcel; pick: number; overrides: Overrides; today: string }) {
  const sc = f.scenarios[pick] ?? f.scenarios[0];
  const sell = f.exit === "sell";
  const edits = overridesToCsv(overrides).trim().split(/\r?\n/).slice(1);
  const sources = scenarioSources(f, sc).slice(0, 9);
  return (
    <Document title={`25x125 feasibility ${p.address ?? f.pin}`} author="25x125">
      <Page size="LETTER" style={s.page}>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <Text style={s.brand}>25x125</Text>
          <Text style={s.muted}>Feasibility one-pager · generated {today}</Text>
        </View>
        <Text style={s.h1}>{titleCase(p.address) || `PIN ${formatPin(f.pin)}`}</Text>
        <Text style={s.muted}>
          {titleCase(p.community_area)} · Ward {p.ward ?? "n/a"} · PIN {formatPin(f.pin)} · {f.zone_class} ·{" "}
          {p.frontage_ft && p.depth_ft ? `${Math.round(p.frontage_ft)} x ${Math.round(p.depth_ft)} ft, ` : ""}
          {Math.round(f.lot_sqft ?? 0).toLocaleString("en-US")} sq ft lot · Exit: {sell ? "build and sell" : "build and hold"}
        </Text>

        <Text style={s.h2}>Scenarios</Text>
        <View style={s.head}>
          <Cell w="26%">Scenario</Cell>
          <Cell w="6%" right>Units</Cell>
          <Cell w="28%" right>Total cost</Cell>
          {sell ? (
            <>
              <Cell w="12%" right>Sale value</Cell>
              <Cell w="10%" right>Profit</Cell>
              <Cell w="8%" right>Return</Cell>
              <Cell w="10%" right>Max land 20%</Cell>
            </>
          ) : (
            <>
              <Cell w="12%" right>Value</Cell>
              <Cell w="10%" right>NOI</Cell>
              <Cell w="8%" right>Yield</Cell>
              <Cell w="10%" right>DSCR loan</Cell>
            </>
          )}
        </View>
        {f.scenarios.map((x, i) => (
          <View key={i} style={[s.row, i === pick ? { backgroundColor: "#E6F1FA" } : {}]}>
            <Cell w="26%">{x.name}</Cell>
            <Cell w="6%" right>{x.units}</Cell>
            <Cell w="28%" right>{usdRange(x.cost_range.central, x.cost_range.low, x.cost_range.high)}</Cell>
            {sell && x.sell ? (
              <>
                <Cell w="12%" right>{usd(x.sell.sale_total)}</Cell>
                <Cell w="10%" right>{usd(x.sell.profit)}</Cell>
                <Cell w="8%" right>{pct(x.sell.return_on_cost)}</Cell>
                <Cell w="10%" right>{usd(x.sell.max_land_price_at["20%"] ?? x.sell.max_land_price)}</Cell>
              </>
            ) : x.hold ? (
              <>
                <Cell w="12%" right>{usd(x.hold.value)}</Cell>
                <Cell w="10%" right>{usd(x.hold.noi)}</Cell>
                <Cell w="8%" right>{pct(x.hold.yield_on_cost)}</Cell>
                <Cell w="10%" right>{usd(x.hold.loan_at_dscr)}</Cell>
              </>
            ) : null}
          </View>
        ))}

        <Text style={s.h2}>Cost · {sc.name}</Text>
        <Text style={s.muted}>
          {sc.gross_sqft.toLocaleString("en-US")} gross sq ft · {sc.cost.preset} spec ${sc.cost.base_per_sqft} per sq ft x {sc.cost.adjustment} area
          adjustment · {sc.cost.stage} stage margins · {sc.cost_range.label}
        </Text>
        {sc.lines.map((l) => (
          <View key={l.id} style={s.row}>
            <Cell w="22%">{l.name}</Cell>
            <Text style={[s.muted, { width: "50%", fontSize: 6.6, paddingRight: 4 }]}>{l.basis}</Text>
            <Cell w="28%" right>{usdRange(l.value, l.low, l.high)}</Cell>
          </View>
        ))}
        <View style={[s.row, { borderBottomWidth: 0 }]}>
          <Cell w="22%" bold>Total cost</Cell>
          <Text style={[s.muted, { width: "50%" }]}>{usd(sc.cost_per_unit)} per unit</Text>
          <Cell w="28%" right bold>{usdRange(sc.cost_range.central, sc.cost_range.low, sc.cost_range.high)}</Cell>
        </View>

        <View style={s.cols}>
          <View style={{ flex: 1 }}>
            <Text style={s.h2}>Result · {sell ? "build and sell" : "build and hold"}</Text>
            {sell && sc.sell ? (
              <>
                <KV k={`Sale value (${sc.units} x ${usd(sc.sell.sale_per_unit)})`} v={usd(sc.sell.sale_total)} />
                {sc.sell.sale_range && (
                  <KV k={`80% sale range (${sc.sell.sale_range.comps} comps)`} v={`${usd(sc.sell.sale_range.low)} to ${usd(sc.sell.sale_range.high)}`} />
                )}
                <KV k="Net sale (x 0.94)" v={usd(sc.sell.net_sale)} />
                <KV k="Profit" v={usd(sc.sell.profit)} />
                <KV k="Return on cost" v={pct(sc.sell.return_on_cost)} />
                <KV k="Margin on net sale" v={pct(sc.sell.margin_on_net_sale)} />
                {Object.entries(sc.sell.max_land_price_at).map(([k, v]) => (
                  <KV key={k} k={`Max land price at ${k} return`} v={usd(v)} />
                ))}
                {sc.sell.range && (
                  <>
                    <KV
                      k="Profit P10 / P25 / P50 / P90"
                      v={`${usd(sc.sell.range.p10)} / ${usd(sc.sell.range.p25)} / ${usd(sc.sell.range.p50)} / ${usd(sc.sell.range.p90)}`}
                    />
                    <KV k={`Draws with a loss (of ${sc.sell.range.draws.toLocaleString("en-US")})`} v={pct(sc.sell.range.loss_share)} />
                  </>
                )}
                {sc.sell.stress_case && <KV k="Stress case: low sale, high cost" v={usd(sc.sell.stress_case.profit)} />}
                <Text style={[s.muted, { marginTop: 2 }]}>15%, 20% and 25% are {sc.sell.reference_lines.label}.</Text>
              </>
            ) : sc.hold ? (
              <>
                <KV k="Rent per unit per month" v={usd(sc.hold.rent_per_unit)} />
                <KV k="Effective gross income" v={usd(sc.hold.effective_gross_income)} />
                <KV k="Operating costs before tax" v={usd(sc.hold.operating_costs_before_tax)} />
                <KV k="Property tax" v={usd(sc.hold.property_tax)} />
                <KV k="Net operating income" v={usd(sc.hold.noi)} />
                <KV k="Value" v={usd(sc.hold.value)} />
                <Text style={s.muted}>{sc.hold.value_basis}</Text>
                <KV k="Yield on cost" v={pct(sc.hold.yield_on_cost, 2)} />
                <KV k="Spread over cap rate" v={`${sc.hold.spread_over_cap_rate_pts.toFixed(2)} pts`} />
                <KV k="Equity created" v={usd(sc.hold.equity_created)} />
                <KV k="Loan at 1.3 DSCR" v={usd(sc.hold.loan_at_dscr)} />
                <KV k="Refinance gap" v={usd(sc.hold.refinance_gap)} />
                <Text style={[s.muted, { marginTop: 2 }]}>
                  {sc.hold.reference_lines.spread_over_cap_rate_pts} pt spread and {sc.hold.reference_lines.dscr} DSCR are{" "}
                  {sc.hold.reference_lines.label}.
                </Text>
              </>
            ) : null}

          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.h2}>Incentives (maximum value; user toggles)</Text>
            {sc.incentives
              .filter((i) => i.applies || i.on)
              .map((i) => (
                <KV key={i.id} k={`${i.on ? "[on]" : "[off]"} ${i.name}`} v={i.kind === "flag" ? "flag" : usd(i.value)} />
              ))}
            {sc.incentives.every((i) => !i.applies && !i.on) && <Text style={s.muted}>None matched to this parcel and exit.</Text>}
            <KV k="Incentive value (toggled on)" v={usd(sc.incentive_total)} />
            <Text style={s.h2}>Code thresholds and flags</Text>
            {[...sc.flags.map((x) => `${x.tag}: ${x.text}`), ...f.zoning_flags.map((z) => z.text)].map((t, i) => (
              <Text key={i}>· {t}</Text>
            ))}
            <Text style={s.h2}>Edited assumptions</Text>
            {edits.length === 0 ? <Text style={s.muted}>None: engine defaults.</Text> : edits.slice(0, 12).map((e) => <Text key={e}>{e.replace(/,/g, " · ")}</Text>)}
          </View>
        </View>

        <Text style={s.h2}>Sources and dates</Text>
        {sources.map((r, i) => (
          <Text key={i} style={{ fontSize: 6.6 }}>
            <Text style={{ fontFamily: "Helvetica-Bold" }}>{r.what}</Text>: {r.source} ({r.asOf})
          </Text>
        ))}
        <Text style={{ fontSize: 6.6 }}>
          <Text style={{ fontFamily: "Helvetica-Bold" }}>Parcel</Text>: Cook County Assessor parcel universe (pabr-t5kh) and City of Chicago zoning
          (dj47-wfun) (pulled {(p.pulled_at ?? "").slice(0, 10)})
        </Text>

        <View style={s.label}>
          <Text style={{ fontFamily: "Helvetica-Bold" }}>{ESTIMATE_LABEL}</Text>
          <Text>
            The numbers show the math from public data and the assumptions above. They do not recommend a project. An Illinois-licensed architect
            must stamp drawings for 3 or more units.
          </Text>
        </View>
      </Page>
    </Document>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <View style={s.row}>
      <Text style={{ width: "58%" }}>{k}</Text>
      <Text style={{ width: "42%", textAlign: "right" }}>{v}</Text>
    </View>
  );
}

export async function GET(req: Request, { params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;
  const url = new URL(req.url);
  const exit = url.searchParams.get("exit") === "hold" ? "hold" : "sell";
  const target = url.searchParams.get("target");
  const pick = Math.max(0, Math.min(2, Number(url.searchParams.get("s") ?? 0) || 0));
  const overrides = overridesFromParam(url.searchParams.get("o"));
  try {
    // Plan check, rate limit and audit row before anything is built.
    await checkExport("pdf", `PIN ${pin}`);
  } catch (e) {
    const status = e instanceof EngineError ? e.status : 500;
    const back = `/parcels/${pin}/feasibility${url.search}`;
    return wallRedirect(req, status, back) ?? new Response(e instanceof Error ? e.message : String(e), { status });
  }
  try {
    const [f, p] = await Promise.all([postFeasibility(pin, exit, target, overrides), getParcel(pin)]);
    const today = new Date().toISOString().slice(0, 10);
    const buf = await renderToBuffer(<Report f={f} p={p} pick={pick} overrides={overrides} today={today} />);
    return new Response(new Uint8Array(buf), {
      headers: {
        "content-type": "application/pdf",
        "content-disposition": `inline; filename="25x125-${f.pin}-${exit}-${today}.pdf"`,
      },
    });
  } catch (e) {
    const status = e instanceof EngineError ? e.status : 500;
    return new Response(`Could not build the PDF: ${e instanceof Error ? e.message : String(e)}`, { status });
  }
}
