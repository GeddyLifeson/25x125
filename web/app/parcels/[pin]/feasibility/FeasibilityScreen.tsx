"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Source } from "../../../../components/Source";
import { feedbackHref, snapshotOf } from "../../../../lib/feedback";
import { num, pct, usd, usdK, usdRange } from "../../../../lib/format";
import { NUMBER_FIELDS, TEXT_CHOICES, mergeOverrides, overridesToCsv, parseOverridesCsv } from "../../../../lib/overrides";
import { ESTIMATE_LABEL, scenarioSources } from "../../../../lib/report";
import type { Feasibility, Overrides, Scenario, ScenarioOverrides } from "../../../../lib/types";

export type Question = { id: string; text: string; type?: string; affects: string[]; if_no?: string; rule?: string };

type Props = {
  pin: string;
  address: string;
  area: string;
  frontage: number | null;
  depth: number | null;
  initial: Feasibility;
  initialExit: "sell" | "hold";
  initialTarget: string | null;
  targets: string[];
  questions: Question[];
  questionsAsOf: string;
  /** Set when the screen was opened from a saved deal: its edits and scenario. */
  deal?: { id: number; scenario: number | null; overrides: Overrides } | null;
  /** Edits saved to the organization for this parcel, when signed in on a plan that keeps them. */
  accountEdits?: { overrides: Overrides; updated_at: string; updated_by: string | null } | null;
  /** null when signed out; otherwise whether the plan saves edits to the account. */
  canSaveEdits?: boolean | null;
};

type NumField = (typeof NUMBER_FIELDS)[number];
type TextField = keyof typeof TEXT_CHOICES;

const FIELD_LABELS: Record<NumField | TextField, string> = {
  units: "Units",
  unit_sqft: "Unit size (sq ft)",
  gross_sqft: "Gross floor area (sq ft)",
  land: "Land price ($)",
  sale_per_unit: "Sale price per unit ($)",
  rent_per_unit: "Rent per unit per month ($)",
  cost_index: "Area cost index",
  escalation: "Cost escalation factor",
  preset: "Build-spec preset",
  stage: "Estimate stage (sets margins)",
  sell_as: "Sell as",
};

const storageKey = (pin: string) => `25x125:overrides:${pin}`;

function currentValue(f: Feasibility, s: Scenario, field: NumField | TextField): string | number | null {
  switch (field) {
    case "units":
      return s.units;
    case "unit_sqft":
      return s.unit_sqft;
    case "gross_sqft":
      return s.gross_sqft;
    case "land":
      return s.cost.land;
    case "sale_per_unit":
      return s.sell?.sale_per_unit ?? null;
    case "rent_per_unit":
      return s.hold?.rent_per_unit ?? s.rent_source?.per_month ?? null;
    case "cost_index":
      return f.inputs.cost_index?.index ?? null;
    case "escalation":
      return f.inputs.escalation?.factor ?? null;
    case "preset":
      return s.cost.preset;
    case "stage":
      return s.cost.stage;
    case "sell_as":
      return s.sale_source?.sell_as ?? "building";
  }
}

function fieldSource(f: Feasibility, s: Scenario, field: NumField | TextField): string {
  const lv = f.inputs.land_value;
  const ci = f.inputs.cost_index;
  switch (field) {
    case "units":
    case "gross_sqft":
      return `Zoning path ${s.name} (${s.path.district}): ${s.path.units} units, ${num(s.path.floor_area_sqft)} sq ft allowed. ${s.path.citations[0] ?? ""}`;
    case "unit_sqft":
      return "Default 1,300 sq ft for 2 units, 1,200 for 3, 1,000 for 4-6 (v1 spec), or the building pattern's size";
    case "land":
      return s.lines.find((l) => l.id === "land")?.basis ?? (lv ? lv.source : "enter the asking price");
    case "sale_per_unit":
      return s.sale_source
        ? `${s.sale_source.source}; ${s.sale_source.comps} comps within ${s.sale_source.radius_mi} mi; adjusted to today`
        : "No comps: enter a price";
    case "rent_per_unit":
      return s.rent_source
        ? `ACS ${s.rent_source.acs_source}, median ${usd(s.rent_source.acs_median)} (margin of error ${usd(s.rent_source.acs_moe)}), x${s.rent_source.growth_since_acs} growth, x${s.rent_source.factor} new-building factor. Range ${usd(s.rent_source.low)} to ${usd(s.rent_source.high)}: ${s.rent_source.range}`
        : "No Census rent: enter a rent";
    case "cost_index":
      return ci ? `Chicago building permits (ydr8-5enu), ${ci.permits} permits${ci.thin ? ", blended with neighbors" : ""}; computed ${ci.computed_on}` : "No index";
    case "escalation":
      return f.inputs.escalation ? `${f.inputs.escalation.basis}; latest month ${f.inputs.escalation.latest_month}` : "";
    case "preset":
      return "Production $165/$170, standard $200/$215, high $250/$265 per sq ft (2-3 / 4-6 units). Default picked by the area cost index. data/rules/feasibility_defaults.json, set 2026-10-29";
    case "stage":
      return "Margins on every line except land: feasibility -20%/+35%, layout -15%/+25%, drawings -10%/+15%, bids -5%/+10% (revised 2026-10-30)";
    case "sell_as":
      return "Whole building uses both comp kinds; condo uses condo comps only";
  }
}

function ProfitBar({ r, stress }: { r: NonNullable<Scenario["sell"]>["range"]; stress: number | null }) {
  if (!r) return null;
  const lo = Math.min(r.p10, stress ?? r.p10, 0);
  const hi = Math.max(r.p90, 0);
  const span = hi - lo || 1;
  const x = (v: number) => `${((v - lo) / span) * 100}%`;
  return (
    <div className="pbar" aria-hidden="true">
      <div className="axis" />
      <div className="band" style={{ left: x(r.p10), width: `calc(${x(r.p90)} - ${x(r.p10)})` }} />
      <div className="core" style={{ left: x(r.p25), width: `calc(${x(r.p50)} - ${x(r.p25)})` }} />
      <div className="tick" style={{ left: x(r.p50) }} />
      <div className="zero" style={{ left: x(0) }} />
      <span className="zl" style={{ left: x(0) }}>
        $0
      </span>
    </div>
  );
}

export function FeasibilityScreen(props: Props) {
  const { pin } = props;
  const [data, setData] = useState<Feasibility>(props.initial);
  const [exit, setExit] = useState<"sell" | "hold">(props.initialExit);
  const [target, setTarget] = useState<string | null>(props.initialTarget);
  const [overrides, setOverrides] = useState<Overrides>(props.deal?.overrides ?? {});
  const [pick, setPick] = useState(props.deal?.scenario ?? 0);
  const [savedDeal, setSavedDeal] = useState<{ id: number; updated: boolean } | null>(null);
  const [savedEdits, setSavedEdits] = useState<string | null>(null);
  const [scope, setScope] = useState<"this" | "all">("this");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0);

  const run = useCallback(
    async (o: Overrides, e: "sell" | "hold", t: string | null) => {
      const my = ++seq.current;
      setBusy(true);
      setError(null);
      const qs = new URLSearchParams({ exit: e });
      if (t) qs.set("target", t);
      try {
        const res = await fetch(`/api/parcels/${pin}/feasibility?${qs}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(o),
        });
        const body = (await res.json()) as Feasibility | { detail: string };
        if (my !== seq.current) return;
        if (!res.ok || "detail" in body) throw new Error("detail" in body ? body.detail : res.statusText);
        setData(body);
        setDirty(false);
        try {
          localStorage.setItem(storageKey(pin), JSON.stringify(o));
        } catch {
          // storage off: edits last for this visit only
        }
        const u = new URL(window.location.href);
        u.searchParams.set("exit", e);
        if (t) u.searchParams.set("target", t);
        else u.searchParams.delete("target");
        window.history.replaceState(null, "", u);
      } catch (err) {
        if (my === seq.current) setError(`Recalculation failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        if (my === seq.current) setBusy(false);
      }
    },
    [pin],
  );

  // Bring back this parcel's saved edits from an earlier visit (not when a deal's edits were loaded).
  useEffect(() => {
    if (props.deal) {
      setNotice(`Loaded the edits saved with deal ${props.deal.id}.`);
      return;
    }
    const acct = props.accountEdits;
    if (acct && Object.keys(acct.overrides).length > 0) {
      setOverrides(acct.overrides);
      setNotice(`Loaded the edits saved to your account on ${acct.updated_at.slice(0, 10)}${acct.updated_by ? ` by ${acct.updated_by}` : ""}.`);
      void run(acct.overrides, props.initialExit, props.initialTarget);
      return;
    }
    try {
      const raw = localStorage.getItem(storageKey(pin));
      const saved = raw ? (JSON.parse(raw) as Overrides) : null;
      if (saved && Object.keys(saved).length > 0) {
        setOverrides(saved);
        setNotice("Your earlier edits for this parcel were restored. Reset to go back to the defaults.");
        void run(saved, props.initialExit, props.initialTarget);
      }
    } catch {
      // ignore bad saved state
    }
  }, [pin, props.initialExit, props.initialTarget, props.deal, props.accountEdits, run]);

  const scenarios = data.scenarios;
  const sel = scenarios[Math.min(pick, scenarios.length - 1)];
  const selKey = String(Math.min(pick, scenarios.length - 1));
  const sell = exit === "sell";

  const scopeKey = scope === "all" ? "all" : selKey;
  const scoped: ScenarioOverrides = overrides[scopeKey] ?? {};
  const effective: ScenarioOverrides = { ...(overrides.all ?? {}), ...(overrides[selKey] ?? {}) };

  const setField = (field: NumField | TextField, raw: string) => {
    setOverrides((prev) => {
      const next: Overrides = JSON.parse(JSON.stringify(prev));
      const t = (next[scopeKey] ??= {}) as Record<string, unknown>;
      if (raw === "") delete t[field];
      else if ((NUMBER_FIELDS as readonly string[]).includes(field)) {
        const n = Number(raw.replace(/[$,\s]/g, ""));
        if (Number.isFinite(n)) t[field] = n;
      } else t[field] = raw;
      if (Object.keys(t).length === 0) delete next[scopeKey];
      return next;
    });
    setDirty(true);
  };

  const toggle = (id: string, on: boolean) => {
    const next = mergeOverrides(overrides, { all: { toggles: { [id]: on } } });
    // A per-scenario toggles set would hide the shared one (the engine merges shallowly), so fold it in.
    for (const k of ["0", "1", "2"]) if (next[k]?.toggles) next[k].toggles = { ...next[k].toggles, [id]: on };
    setOverrides(next);
    void run(next, exit, target);
  };

  const answer = (id: string, v: string) => {
    const next: Overrides = JSON.parse(JSON.stringify(overrides));
    const all = (next.all ??= {});
    const answers = { ...(all.answers ?? {}) };
    if (v === "") delete answers[id];
    else answers[id] = v === "yes" ? true : v === "no" ? false : Number(v);
    all.answers = answers;
    if (Object.keys(answers).length === 0) delete all.answers;
    if (Object.keys(all).length === 0) delete next.all;
    setOverrides(next);
    void run(next, exit, target);
  };

  const switchExit = (e: "sell" | "hold") => {
    setExit(e);
    void run(overrides, e, target);
  };

  const switchTarget = (t: string) => {
    const v = t || null;
    setTarget(v);
    void run(overrides, exit, v);
  };

  const reset = () => {
    setOverrides({});
    setNotice(null);
    try {
      localStorage.removeItem(storageKey(pin));
    } catch {
      // ignore
    }
    void run({}, exit, target);
  };

  // Save the scenario on screen, with its edits, as a deal; the engine re-runs it and stores the numbers.
  const saveDeal = async (update: boolean) => {
    setError(null);
    const body = { pin, exit, target, scenario: Number(selKey), overrides };
    const url = update && props.deal ? `/api/deals/${props.deal.id}` : "/api/deals";
    try {
      const res = await fetch(url, {
        method: update ? "PATCH" : "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(update ? { exit, target, scenario: Number(selKey), overrides } : { ...body, stage: "feasibility" }),
      });
      const d = (await res.json()) as { id?: number; detail?: string };
      if (!res.ok || !d.id) throw new Error(d.detail ?? res.statusText);
      setSavedDeal({ id: d.id, updated: update });
    } catch (e) {
      setError(`Could not save the deal: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  // Keep the edits on screen with the organization, so they follow the user to another computer and teammates.
  const saveEdits = async () => {
    setError(null);
    try {
      const res = await fetch(`/api/overrides/${pin}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ exit, target, overrides }),
      });
      const d = (await res.json()) as { updated_at?: string; detail?: string };
      if (!res.ok) throw new Error(d.detail ?? res.statusText);
      setSavedEdits(`Saved ${editCount} edit${editCount === 1 ? "" : "s"} to your account.`);
    } catch (e) {
      setError(`Could not save the edits: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const downloadAssumptions = () => {
    const blob = new Blob([overridesToCsv(overrides)], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `25x125-assumptions-${pin}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const importAssumptions = async (file: File) => {
    const text = await file.text();
    const { overrides: o, errors, count } = parseOverridesCsv(text);
    if (errors.length) setError(`Import: ${errors.slice(0, 5).join("; ")}${errors.length > 5 ? ` (+${errors.length - 5} more)` : ""}`);
    if (count > 0) {
      const next = mergeOverrides(overrides, o);
      setOverrides(next);
      setNotice(`Imported ${count} value(s) from ${file.name}.`);
      void run(next, exit, target);
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const linkQs = useMemo(() => {
    const qs = new URLSearchParams({ exit, s: selKey });
    if (target) qs.set("target", target);
    if (Object.keys(overrides).length) qs.set("o", JSON.stringify(overrides));
    return qs.toString();
  }, [exit, selKey, target, overrides]);

  const editCount = Object.values(overrides).reduce(
    (n, s) => n + Object.entries(s).reduce((m, [k, v]) => m + (k === "toggles" || k === "answers" ? Object.keys(v as object).length : 1), 0),
    0,
  );
  const allFlags: { tag: string; text: string; citation?: string | null }[] = [
    ...(sel?.flags ?? []),
    ...data.zoning_flags.map((z) => ({ tag: "Cost", text: z.text, citation: z.citation })),
  ];
  const togglesOn = (overrides.all?.toggles ?? {}) as Record<string, boolean>;
  const answers = (overrides.all?.answers ?? {}) as Record<string, boolean | number>;

  if (!sel) {
    return (
      <main className="wrap">
        <Link href={`/parcels/${pin}`}>Back to parcel</Link>
        <p className="err">The engine returned no scenarios for this parcel.</p>
      </main>
    );
  }

  const cardResult = (s: Scenario) =>
    sell
      ? { k1: "Profit", v1: usdK(s.sell?.profit), k2: "Return on cost", v2: pct(s.sell?.return_on_cost) }
      : { k1: "Net operating income", v1: usdK(s.hold?.noi), k2: "Yield on cost", v2: pct(s.hold?.yield_on_cost, 2) };

  // "Check these numbers": the feedback form, with this scenario's figures on screen carried over.
  const checkHref = (s: Scenario, i: number) => feedbackHref(pin, i, snapshotOf(data, s, data.exit, editCount, props.address));

  const fields: (NumField | TextField)[] = [
    "units",
    "unit_sqft",
    "gross_sqft",
    "land",
    sell ? "sale_per_unit" : "rent_per_unit",
    sell ? "rent_per_unit" : "sale_per_unit",
    "cost_index",
    "escalation",
    "preset",
    "stage",
    "sell_as",
  ];

  return (
    <main className="wrap">
      <section className="head">
        <div>
          <Link href={`/parcels/${pin}`} style={{ fontSize: 13 }}>
            Back to parcel
          </Link>
          <h1>Feasibility · {props.address}</h1>
          <span className="muted">
            {props.area} · {data.zone_class} ·{" "}
            {props.frontage && props.depth ? `${num(props.frontage)} x ${num(props.depth)}` : `${num(data.lot_sqft)} sq ft`} · priced from
            new-construction sales near the lot, not citywide averages
          </span>
        </div>
        <div className="btns">
          {props.targets.length > 0 && (
            <label className="small muted" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              Rezoning target
              <select
                value={target ?? props.targets[0]}
                onChange={(e) => switchTarget(e.target.value === props.targets[0] ? "" : e.target.value)}
                style={{ height: 44, borderRadius: 6, border: "1px solid #c9cfd5", padding: "0 8px", font: "inherit" }}
              >
                {props.targets.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div role="group" aria-label="Exit" className="seg">
            <button type="button" aria-pressed={sell} onClick={() => switchExit("sell")}>
              Build and sell
            </button>
            <button type="button" aria-pressed={!sell} onClick={() => switchExit("hold")}>
              Build and hold
            </button>
          </div>
        </div>
      </section>

      <div className="bar">
        <span className="status" role="status">
          {busy ? "Recalculating..." : `${editCount} edit${editCount === 1 ? "" : "s"} applied · ${ESTIMATE_LABEL}`}
        </span>
        {notice && <span className="status">{notice}</span>}
        {error && <span className="err">{error}</span>}
      </div>

      <section aria-label="Scenarios" className="cards">
        {scenarios.map((s, i) => {
          const r = cardResult(s);
          return (
            <button type="button" key={i} className="sc" aria-pressed={i === pick} onClick={() => setPick(i)}>
              <span className="row">
                <span className="nm">{s.name}</span>
                <span className="mono small muted">{s.units} units</span>
              </span>
              <span className="small muted">{s.approval}</span>
              <span className="kv">
                <span>
                  <span className="k">{r.k1}</span>
                  <span className="v">{r.v1}</span>
                </span>
                <span>
                  <span className="k">{r.k2}</span>
                  <span className="v">{r.v2}</span>
                </span>
              </span>
            </button>
          );
        })}
      </section>
      {scenarios.length < 3 && (
        <p className="small muted" style={{ marginTop: -10 }}>
          {scenarios.length} scenario{scenarios.length === 1 ? "" : "s"}: the engine found no other zoning path with a building pattern that fits
          this lot{target ? ` and the ${target} target` : ""}.
        </p>
      )}

      <div className="cols">
        <div className="main">
          <section className="card">
            <div className="row" style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
              <h2>Cost · {sel.name}</h2>
              <Link className="btn small" href={checkHref(sel, Math.min(pick, scenarios.length - 1))} data-testid="check-numbers">
                Check these numbers
              </Link>
            </div>
            <p className="sub">
              {num(sel.gross_sqft)} gross sq ft · hard cost ${sel.cost.base_per_sqft} per sq ft ({sel.cost.preset} spec) x {sel.cost.adjustment} area
              adjustment · margins for the {sel.cost.stage} stage
            </p>
            <div className="scroll">
              <table className="t">
                <thead>
                  <tr>
                    <th>Line</th>
                    <th className="num">Central</th>
                    <th className="num">Low to high</th>
                  </tr>
                </thead>
                <tbody>
                  {sel.lines.map((l) => (
                    <tr key={l.id}>
                      <td>
                        {l.name}
                        <div className="basis">{l.basis}</div>
                      </td>
                      <td className="num">{usd(l.value)}</td>
                      <td className="num muted">{l.low === l.high ? "no margin" : `${usd(l.low)} to ${usd(l.high)}`}</td>
                    </tr>
                  ))}
                  <tr className="total">
                    <td>
                      Total cost
                      <div className="basis">
                        {usdRange(sel.cost_per_unit, sel.cost_per_unit + sel.cost_range.low_margin / sel.units, sel.cost_per_unit + sel.cost_range.high_margin / sel.units)}{" "}
                        per unit · {sel.cost_range.label}
                      </div>
                    </td>
                    <td className="num" colSpan={2}>
                      {usdRange(sel.cost_range.central, sel.cost_range.low, sel.cost_range.high)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>Scenarios side by side</h2>
            <p className="sub">Same assumptions, each zoning path. Click a scenario card to see its cost lines.</p>
            <div className="scroll">
              <table className="t">
                <thead>
                  <tr>
                    <th></th>
                    {scenarios.map((s, i) => (
                      <th key={i} className="num">
                        {s.name.split(" · ")[0]} · {s.units} units
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["Approval", (s: Scenario) => s.approval, false],
                      ["Gross floor area", (s: Scenario) => `${num(s.gross_sqft)} sq ft`, true],
                      ["Land", (s: Scenario) => usd(s.cost.land), true],
                      ["Total cost", (s: Scenario) => usd(s.cost_range.central), true],
                      ["Cost range", (s: Scenario) => `-${usd(-s.cost_range.low_margin)} / +${usd(s.cost_range.high_margin)}`, true],
                      ["Cost per unit", (s: Scenario) => usd(s.cost_per_unit), true],
                      ...(sell
                        ? ([
                            ["Sale value", (s: Scenario) => usd(s.sell?.sale_total), true],
                            ["Profit", (s: Scenario) => usd(s.sell?.profit), true],
                            ["Return on cost", (s: Scenario) => pct(s.sell?.return_on_cost), true],
                            ["Max land price at 20%", (s: Scenario) => usd(s.sell?.max_land_price_at["20%"]), true],
                            ["Profit P10 to P90", (s: Scenario) => (s.sell?.range ? `${usdK(s.sell.range.p10)} to ${usdK(s.sell.range.p90)}` : "n/a"), true],
                            ["Draws with a loss", (s: Scenario) => pct(s.sell?.range?.loss_share), true],
                          ] as const)
                        : ([
                            ["Net operating income", (s: Scenario) => usd(s.hold?.noi), true],
                            ["Value", (s: Scenario) => usd(s.hold?.value), true],
                            ["Yield on cost", (s: Scenario) => pct(s.hold?.yield_on_cost, 2), true],
                            ["Loan at 1.3 DSCR", (s: Scenario) => usd(s.hold?.loan_at_dscr), true],
                            ["Refinance gap", (s: Scenario) => usd(s.hold?.refinance_gap), true],
                          ] as const)),
                      ["Incentive value", (s: Scenario) => usd(s.incentive_total), true],
                    ] as const
                  ).map(([label, fn, isNum]) => (
                    <tr key={label}>
                      <td>{label}</td>
                      {scenarios.map((s, i) => (
                        <td key={i} className={isNum ? "num" : "small"} style={i === pick ? { background: "#E6F1FA" } : undefined}>
                          {fn(s)}
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Your check</td>
                    {scenarios.map((s, i) => (
                      <td key={i} className="num" style={i === pick ? { background: "#E6F1FA" } : undefined}>
                        <Link className="btn small" href={checkHref(s, i)} data-testid={`check-numbers-${"ABC"[i]}`}>
                          Check these numbers
                        </Link>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2 style={{ marginBottom: 14 }}>Code thresholds this scenario crosses</h2>
            <ul className="plain flags">
              {allFlags.map((f, i) => (
                <li key={i}>
                  <span className={`tag${/adds|risk|verify|cost/i.test(f.tag) ? " c" : ""}`}>{f.tag}</span>
                  <span>
                    {f.text} {f.citation ? <Source label="rule">{f.citation}</Source> : null}
                  </span>
                </li>
              ))}
              {sel.buyer_financing && (
                <li>
                  <span className="tag">Buyers</span>
                  <span>
                    {sel.buyer_financing.class}
                    {sel.buyer_financing.fha_limit
                      ? `; FHA limit ${usd(sel.buyer_financing.fha_limit)}${sel.buyer_financing.over_fha_limit ? ", sale price per building is over it" : ""}`
                      : ""}
                  </span>
                </li>
              )}
            </ul>
          </section>

          <section className="card">
            <h2>Assumptions</h2>
            <p className="sub">
              Every default can be changed. Blank fields use the engine default shown below each box. Edited fields are outlined in blue.
            </p>
            <div className="bar" style={{ marginBottom: 12 }}>
              <span className="small muted">Apply edits to</span>
              <div role="group" aria-label="Apply edits to" className="seg">
                <button type="button" aria-pressed={scope === "this"} onClick={() => setScope("this")} style={{ height: 34 }}>
                  {sel.name.split(" · ")[0]} only
                </button>
                <button type="button" aria-pressed={scope === "all"} onClick={() => setScope("all")} style={{ height: 34 }}>
                  All scenarios
                </button>
              </div>
            </div>
            <form
              className="form"
              onSubmit={(e) => {
                e.preventDefault();
                void run(overrides, exit, target);
              }}
            >
              {fields.map((field) => {
                const cur = currentValue(data, sel, field);
                const val = (scoped as Record<string, unknown>)[field];
                const inherited = scope === "this" && val === undefined ? (effective as Record<string, unknown>)[field] : undefined;
                const isText = field in TEXT_CHOICES;
                return (
                  <label key={field}>
                    {FIELD_LABELS[field]}
                    {isText ? (
                      <select
                        className={val !== undefined ? "set" : undefined}
                        value={val === undefined ? "" : String(val)}
                        onChange={(e) => setField(field, e.target.value)}
                      >
                        <option value="">Default ({String(cur ?? "n/a")})</option>
                        {TEXT_CHOICES[field as TextField].map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        inputMode="decimal"
                        className={val !== undefined ? "set" : undefined}
                        value={val === undefined ? "" : String(val)}
                        placeholder={cur === null ? "n/a" : String(typeof cur === "number" ? Math.round(cur * 10000) / 10000 : cur)}
                        onChange={(e) => setField(field, e.target.value)}
                      />
                    )}
                    <span className="def">
                      Now {typeof cur === "number" ? (field === "cost_index" || field === "escalation" ? cur.toFixed(3) : num(cur)) : (cur ?? "n/a")}
                      {inherited !== undefined ? " (set for all scenarios)" : ""} <Source>{fieldSource(data, sel, field)}</Source>
                    </span>
                  </label>
                );
              })}
              <div className="bar" style={{ gridColumn: "1 / -1" }}>
                <button className="btn primary small" type="submit" disabled={busy}>
                  Recalculate
                </button>
                <button className="btn small" type="button" onClick={reset} disabled={busy}>
                  Reset to defaults
                </button>
                {dirty && <span className="status">Edits not yet applied.</span>}
              </div>
            </form>
          </section>

          <section className="card">
            <h2>Sources behind this scenario</h2>
            <p className="sub">Where each input comes from and when it was pulled or computed.</p>
            <div className="scroll">
              <table className="t">
                <thead>
                  <tr>
                    <th>Input</th>
                    <th>Source</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarioSources(data, sel).map((r, i) => (
                    <tr key={i}>
                      <td>{r.what}</td>
                      <td className="small">{r.source}</td>
                      <td className="small" style={{ whiteSpace: "nowrap" }}>
                        {r.asOf}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="side">
          <section className="card dark">
            <h2>Result · {sell ? "build and sell" : "build and hold"}</h2>
            {sell && sel.sell ? <SellBlock s={sel} /> : sel.hold ? <HoldBlock s={sel} /> : <p>No result for this exit.</p>}
          </section>

          <section className="card">
            <h2>Incentives</h2>
            <p className="sub small">Shows the maximum. Turn off what doesn&apos;t apply to you.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {sel.incentives.map((i) => (
                <label key={i.id} className={`inc${i.applies ? "" : " na"}`}>
                  <input
                    type="checkbox"
                    checked={i.on}
                    disabled={busy}
                    onChange={(e) => toggle(i.id, e.target.checked)}
                    aria-label={i.name}
                  />
                  <span>
                    <span>{i.name}</span>
                    <span className="small muted">
                      {i.basis}
                      {i.note ? `. ${i.note}` : ""}
                      {!i.applies ? ". Not matched to this parcel or exit." : ""}
                      {togglesOn[i.id] !== undefined ? " (you set this)" : ""}
                    </span>
                  </span>
                  <span className="val">{i.kind === "flag" ? "flag" : usd(i.on ? i.value : 0)}</span>
                </label>
              ))}
            </div>
            <div className="sumrow">
              <span>Incentive value</span>
              <span className="mono">{usd(sel.incentive_total)}</span>
            </div>
            <p className="small muted" style={{ marginTop: 8 }}>
              Cash items (Enterprise Zone) are already a cost line above. Tax and deferral items are shown apart from profit.
            </p>
          </section>

          <section className="card">
            <h2>Eligibility questions</h2>
            <p className="sub small">
              Answers switch incentives off when they can&apos;t apply. Unanswered questions keep the maximum.{" "}
              <Source>data/rules/incentive_questions.json, as of {props.questionsAsOf}</Source>
            </p>
            <div className="form" style={{ gridTemplateColumns: "1fr" }}>
              {props.questions.map((q) => (
                <label key={q.id}>
                  {q.text}
                  {q.type === "number" ? (
                    <input
                      inputMode="numeric"
                      className={answers[q.id] !== undefined ? "set" : undefined}
                      defaultValue={answers[q.id] === undefined ? "" : String(answers[q.id])}
                      placeholder="years"
                      onBlur={(e) => {
                        if (e.target.value !== String(answers[q.id] ?? "")) answer(q.id, e.target.value);
                      }}
                    />
                  ) : (
                    <select
                      className={answers[q.id] !== undefined ? "set" : undefined}
                      value={answers[q.id] === undefined ? "" : answers[q.id] ? "yes" : "no"}
                      onChange={(e) => answer(q.id, e.target.value)}
                    >
                      <option value="">Not answered</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  )}
                  <span className="def">Affects: {q.affects.join(", ")}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="card">
            <h2>Export and import</h2>
            <p className="sub small">The PDF and CSV use the assumptions on screen.</p>
            <div className="bar">
              <a className="btn primary small" href={`/parcels/${pin}/report.pdf?${linkQs}`} target="_blank" rel="noreferrer">
                One-page PDF
              </a>
              <a className="btn small" href={`/parcels/${pin}/feasibility.csv?${linkQs}`}>
                Lines as CSV
              </a>
              <button className="btn small" type="button" onClick={downloadAssumptions}>
                Assumptions CSV
              </button>
              <button className="btn small" type="button" onClick={() => fileRef.current?.click()}>
                Import assumptions
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                hidden
                data-testid="import"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void importAssumptions(f);
                }}
              />
            </div>
            <p className="small muted" style={{ marginTop: 10 }}>
              Import file: one row per value, <span className="mono">field,value</span> or <span className="mono">scenario,field,value</span>{" "}
              (scenario all, A, B or C). Fields: {[...NUMBER_FIELDS, ...Object.keys(TEXT_CHOICES)].join(", ")}, toggle.&lt;incentive&gt;,
              answer.&lt;question&gt;.
            </p>
          </section>

          <section className="card">
            <h2>Deal</h2>
            <p className="sub small">Saves scenario {sel.name} with the {editCount} edit{editCount === 1 ? "" : "s"} on screen. The engine runs it again and keeps the numbers with the date.</p>
            <div className="bar">
              {props.deal && (
                <button className="btn primary small" type="button" onClick={() => void saveDeal(true)} data-testid="update-deal">
                  Update deal {props.deal.id}
                </button>
              )}
              <button className={`btn small${props.deal ? "" : " primary"}`} type="button" onClick={() => void saveDeal(false)} data-testid="save-deal">
                {props.deal ? "Save as a new deal" : "Save scenario to deal"}
              </button>
              {props.canSaveEdits && (
                <button className="btn small" type="button" onClick={() => void saveEdits()} data-testid="save-edits">
                  Save edits to account
                </button>
              )}
            </div>
            {props.canSaveEdits === null && (
              <p className="small muted" style={{ marginTop: 8 }}>
                <Link href={`/signin?next=${encodeURIComponent(`/parcels/${pin}/feasibility`)}`}>Sign in</Link> to save deals, keep edits
                with your account and export the PDF and CSV. Without an account, edits stay in this browser.
              </p>
            )}
            {savedEdits && (
              <p className="small" role="status" style={{ marginTop: 8 }}>
                {savedEdits}
              </p>
            )}
            {savedDeal && (
              <p className="small" role="status" style={{ marginTop: 8 }}>
                {savedDeal.updated ? "Updated" : "Saved as"} deal {savedDeal.id}. <Link href={`/deals?d=${savedDeal.id}`}>Open deals</Link>
              </p>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}

function KV({ k, v, src, small }: { k: string; v: string; src?: string; small?: boolean }) {
  return (
    <div className="kvrow">
      <span className="k">
        {k} {src && <Source>{src}</Source>}
      </span>
      <span className={`v${small ? " sm" : ""}`}>{v}</span>
    </div>
  );
}

function SellBlock({ s }: { s: Scenario }) {
  const x = s.sell!;
  const src = s.sale_source;
  return (
    <>
      <KV
        k={`Sale value (${s.units} x ${usd(x.sale_per_unit)})`}
        v={usd(x.sale_total)}
        src={src ? `${src.source}; ${src.comps} comps within ${src.radius_mi} mi; sold as ${src.sell_as}${src.notes.length ? `; ${src.notes.join("; ")}` : ""}` : "entered"}
      />
      {x.sale_range && (
        <KV k={`80% sale range (${x.sale_range.comps} comps)`} v={`${usdK(x.sale_range.low)} to ${usdK(x.sale_range.high)}`} small src={x.sale_range.label} />
      )}
      <KV k="Net sale" v={usd(x.net_sale)} src={x.net_sale_basis} />
      <KV k="Profit" v={usd(x.profit)} src="net sale - total cost" />
      <KV k="Return on cost" v={pct(x.return_on_cost)} src="profit / total cost" />
      <KV k="Margin on net sale" v={pct(x.margin_on_net_sale)} src="profit / net sale" />
      <hr />
      <span className="small">Max land price (residual land value) at a return on cost of</span>
      <div className="refs">
        {Object.entries(x.max_land_price_at).map(([k, v]) => (
          <span key={k}>
            <span className="k">{k}</span>
            <span className="v">{usdK(v)}</span>
          </span>
        ))}
      </div>
      <span className="small">
        15%, 20% and 25% are {x.reference_lines.label}. Land in this run: {usd(s.cost.land)}.
      </span>
      {x.range && (
        <>
          <hr />
          <span className="small">
            Profit over {x.range.draws.toLocaleString("en-US")} draws of sale and cost{" "}
            <Source>{`${x.range.label}; seed ${x.range.seed}; sale-cost correlation ${x.range.sale_cost_correlation}`}</Source>
          </span>
          <div className="refs">
            {(["p10", "p25", "p50", "p90"] as const).map((k) => (
              <span key={k}>
                <span className="k">{k.toUpperCase()}</span>
                <span className="v">{usdK(x.range![k])}</span>
              </span>
            ))}
          </div>
          <ProfitBar r={x.range} stress={x.stress_case?.profit ?? null} />
          <KV k="Share of draws with a loss" v={pct(x.range.loss_share)} small />
        </>
      )}
      {x.stress_case && <KV k="Stress case: low sale and high cost" v={usd(x.stress_case.profit)} small src={x.stress_case.label} />}
    </>
  );
}

function HoldBlock({ s }: { s: Scenario }) {
  const h = s.hold!;
  const r = s.rent_source;
  return (
    <>
      <KV
        k={`Rent per unit per month`}
        v={usd(h.rent_per_unit)}
        src={r ? `ACS ${r.acs_source}; x${r.growth_since_acs} growth; x${r.factor} new-building factor` : "entered"}
      />
      {h.rent_range && <KV k="Rent range" v={`${usd(h.rent_range.low)} to ${usd(h.rent_range.high)}`} small src={r?.range} />}
      <KV k="Effective gross income" v={usd(h.effective_gross_income)} src="rent x 12 x units x 0.95 occupancy" />
      <KV k="Operating costs before tax" v={usd(h.operating_costs_before_tax)} />
      <KV k="Property tax" v={usd(h.property_tax)} />
      <KV k="Net operating income" v={usd(h.noi)} />
      <KV k="Value" v={usd(h.value)} src={h.value_basis} />
      <KV k="Yield on cost" v={pct(h.yield_on_cost, 2)} src="NOI / total cost" />
      <KV k="Spread over cap rate" v={`${h.spread_over_cap_rate_pts.toFixed(2)} pts`} small />
      <KV k="Equity created" v={usd(h.equity_created)} src="value - total cost" />
      <hr />
      <KV k="Loan at 1.3 DSCR" v={usd(h.loan_at_dscr)} src={h.loan_at_dscr_basis} />
      <KV k="Refinance gap" v={usd(h.refinance_gap)} src="construction loan (65% of total cost) - loan at DSCR: what a refinance would not cover" />
      <span className="small">
        A {h.reference_lines.spread_over_cap_rate_pts}-point spread over the cap rate and a {h.reference_lines.dscr} DSCR are{" "}
        {h.reference_lines.label}.
      </span>
    </>
  );
}
