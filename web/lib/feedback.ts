// Feedback on the app's numbers (engine/feedback.py). The feasibility screen passes the figures on screen to
// /feedback in the address, so the entry stores exactly what the person was looking at.
import type { Feasibility, Scenario } from "./types";

/** The app's figures on screen when the form was opened (dollars unless named otherwise). */
export type Snapshot = {
  total_cost?: number;
  cost_per_unit?: number;
  hard_cost_per_sqft?: number;
  total_cost_per_sqft?: number;
  sale_per_unit?: number;
  profit?: number;
  max_land_price?: number;
  cost_index?: number;
  area_adjustment?: number;
  units?: number;
  gross_sqft?: number;
  edits?: number;
  preset?: string;
  exit?: string;
  scenario_name?: string;
  stage?: string;
  address?: string;
};

// Snapshot field -> short address parameter.
const PARAMS: Record<keyof Snapshot, string> = {
  total_cost: "total",
  cost_per_unit: "per_unit",
  hard_cost_per_sqft: "hard_sqft",
  total_cost_per_sqft: "total_sqft",
  sale_per_unit: "sale",
  profit: "profit",
  max_land_price: "max_land",
  cost_index: "index",
  area_adjustment: "adj",
  units: "units",
  gross_sqft: "gsf",
  edits: "edits",
  preset: "preset",
  exit: "exit",
  scenario_name: "name",
  stage: "stage",
  address: "address",
};
const TEXT_KEYS = new Set<keyof Snapshot>(["preset", "exit", "scenario_name", "stage", "address"]);

const round2 = (n: number) => Math.round(n * 100) / 100;

export function snapshotOf(f: Feasibility, s: Scenario, exit: "sell" | "hold", edits: number, address: string): Snapshot {
  const gsf = s.cost.gfa_sqft || s.gross_sqft;
  return {
    total_cost: Math.round(s.cost_range.central),
    cost_per_unit: Math.round(s.cost_per_unit),
    hard_cost_per_sqft: gsf ? round2(s.cost.hard / gsf) : undefined,
    total_cost_per_sqft: gsf ? round2(s.cost_range.central / gsf) : undefined,
    sale_per_unit: s.sell?.sale_per_unit != null ? Math.round(s.sell.sale_per_unit) : undefined,
    profit: s.sell?.profit != null ? Math.round(s.sell.profit) : undefined,
    max_land_price: s.sell?.max_land_price_at?.["20%"] != null ? Math.round(s.sell.max_land_price_at["20%"]) : undefined,
    cost_index: f.inputs.cost_index?.index ?? undefined,
    area_adjustment: s.cost.adjustment,
    units: s.units,
    gross_sqft: Math.round(gsf),
    edits,
    preset: s.cost.preset,
    exit,
    scenario_name: s.name,
    stage: s.cost.stage,
    address,
  };
}

/** /feedback?pin=...&scenario=A&total=... for one scenario on the feasibility screen. */
export function feedbackHref(pin: string, scenarioIndex: number, snap: Snapshot): string {
  const qs = new URLSearchParams({ pin, scenario: "ABC"[scenarioIndex] ?? "A", from: `/parcels/${pin}/feasibility` });
  for (const [k, p] of Object.entries(PARAMS) as [keyof Snapshot, string][]) {
    const v = snap[k];
    if (v !== undefined && v !== null && v !== "") qs.set(p, String(v));
  }
  return `/feedback?${qs}`;
}

export function snapshotFromParams(sp: Record<string, string | string[] | undefined>): Snapshot {
  const out: Snapshot = {};
  for (const [k, p] of Object.entries(PARAMS) as [keyof Snapshot, string][]) {
    const raw = sp[p];
    const v = Array.isArray(raw) ? raw[0] : raw;
    if (v === undefined || v === "") continue;
    if (TEXT_KEYS.has(k)) (out as Record<string, string>)[k] = v.slice(0, 200);
    else {
      const n = Number(v);
      if (Number.isFinite(n)) (out as Record<string, number>)[k] = n;
    }
  }
  return out;
}

export type Spread = { median: number; low: number; high: number } | null;
export type Comparison = { own: number; app: number; difference: number; ratio: number };

export type FeedbackRow = {
  id: number;
  created_at: string;
  email: string | null;
  user_id: string | null;
  org_id: string | null;
  page_path: string | null;
  pin: string | null;
  scenario: string | null;
  screen: string | null;
  rating: number | null;
  cost_per_sqft_own: number | null;
  cost_total_own: number | null;
  sale_per_unit_own: number | null;
  numbers_wrong: string | null;
  outside_questions: string | null;
  missing: string | null;
  minutes_spent: number | null;
  would_use: "yes" | "maybe" | "no" | null;
  notes: string | null;
  app_snapshot: Snapshot;
  comparisons: Partial<Record<"cost_per_sqft" | "cost_total" | "sale_per_unit", Comparison>>;
};

export type FeedbackSummary = {
  count: number;
  rating: { n: number; median: number | null };
  comparisons: Record<
    "cost_per_sqft" | "cost_total" | "sale_per_unit",
    { label: string; n: number; ratio: Spread; difference: Spread; own_median: number | null; app_median: number | null }
  >;
  would_use: { yes: number; maybe: number; no: number };
  minutes_spent: { n: number; total: number };
  note: string;
};
