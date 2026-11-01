"use client";
import Link from "next/link";
import { useState } from "react";
import { num, pct, titleCase, usd } from "../lib/format";
import { INCENTIVE_LABELS, PENALTY_LABELS, SCORE_LABEL, SCORE_PARTS, SCORE_SOURCE, SIGNAL_LABELS } from "../lib/labels";
import type { Lot } from "../lib/types";
import { Source } from "./Source";

/** The map's side panel: one lot's points by part, what earned them, and links onward. */
export function LotPanel({ lot, onClose }: { lot: Lot; onClose: () => void }) {
  const [saved, setSaved] = useState<{ id: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const d = lot.details;

  const save = async () => {
    setErr(null);
    const res = await fetch("/api/deals", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pin: lot.pin, stage: "lead" }),
    });
    const body = (await res.json()) as { id?: number; detail?: string };
    if (res.ok && body.id) setSaved({ id: body.id });
    else setErr(body.detail ?? res.statusText);
  };

  return (
    <aside className="lotpanel" aria-label="Selected lot" data-testid="panel">
      <div className="lp-head">
        <div>
          <h2>{titleCase(lot.address) || `Lot ${lot.pin10}`}</h2>
          <span className="small muted">
            {lot.zone_class ?? "n/a"} · {lot.lot_sqft ? `${num(lot.lot_sqft)} sq ft` : "lot size n/a"} · {titleCase(lot.community_area)}
          </span>
        </div>
        <button type="button" className="x" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <div className="lp-score">
        <span className="mono big">{num(lot.score)}</span>
        <span className="small muted">
          Development score, 0 to 100. {SCORE_LABEL} <Source>{`${SCORE_SOURCE}; computed ${lot.computed_on}`}</Source>
        </span>
      </div>
      <table className="t pts">
        <tbody>
          {SCORE_PARTS.map((p) => (
            <tr key={p.key}>
              <td>
                {p.label} <Source label="how">{p.how}</Source>
              </td>
              <td className="num">
                {num(lot[p.key], 1)} <span className="muted">/ {p.max}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="plain lp-why">
        <li>
          <span>Units by right</span>
          <span className="mono">
            {lot.by_right_units ?? 0} allowed, {lot.units_now ?? 0} standing
          </span>
        </li>
        <li>
          <span>Signals</span>
          <span>{(d.signals ?? []).map((s) => SIGNAL_LABELS[s] ?? s).join(", ") || "none"}</span>
        </li>
        <li>
          <span>Penalties</span>
          <span>{(d.penalties ?? []).map((s) => PENALTY_LABELS[s] ?? s).join(", ") || "none"}</span>
        </li>
        <li>
          <span>Incentives counted</span>
          <span>{(d.incentives ?? []).map((s) => INCENTIVE_LABELS[s] ?? s).join(", ") || "none"}</span>
        </li>
        <li>
          <span>Fast path</span>
          <span>{d.fast_path ? "Yes: by right, no zoning relief, 2-8 units" : "No"}</span>
        </li>
      </ul>
      <h3>By-right program, build and sell</h3>
      {lot.units_priced ? (
        <ul className="plain">
          <li>
            <span>Program priced</span>
            <span className="mono">{lot.units_priced} units</span>
          </li>
          <li>
            <span>
              Sale per unit <Source>{`Cook County Assessor new-construction sales; ${lot.sale_comps ?? 0} comps; nightly estimate at the lot's grid cell, ${lot.computed_on}`}</Source>
            </span>
            <span className="mono">{usd(lot.sale_per_unit)}</span>
          </li>
          <li>
            <span>Land in the math</span>
            <span className="mono">{usd(lot.land)}</span>
          </li>
          <li>
            <span>Total cost</span>
            <span className="mono">{usd(lot.total_cost)}</span>
          </li>
          <li>
            <span>Profit, central / 25th percentile</span>
            <span className="mono">
              {usd(lot.profit_central)} / {usd(lot.profit_p25)}
            </span>
          </li>
          <li>
            <span>Return on cost, central / 25th percentile</span>
            <span className="mono">
              {pct(lot.return_on_cost)} / {pct(lot.return_on_cost_p25)}
            </span>
          </li>
          <li>
            <span>Max land price</span>
            <span className="mono">{usd(lot.max_land_price)}</span>
          </li>
        </ul>
      ) : null}
      {d.profit && <p className="small warnline">No profit points: {d.profit}.</p>}
      <p className="small muted">Nightly figures for sorting. The feasibility screen prices the lot itself, with margins on every line.</p>
      <div className="bar">
        <Link className="btn small" href={`/parcels/${lot.pin}`}>
          Parcel page
        </Link>
        <Link className="btn primary small" href={`/parcels/${lot.pin}/feasibility`}>
          Run feasibility
        </Link>
        {saved ? (
          <Link className="btn small" href={`/deals?d=${saved.id}`}>
            Saved as deal {saved.id}
          </Link>
        ) : (
          <button type="button" className="btn small" onClick={() => void save()}>
            Save as deal
          </button>
        )}
      </div>
      {err && <p className="err">{err}</p>}
    </aside>
  );
}
