// Plain-English names for the score's signal, penalty and incentive ids (jobs/score_parcels.py,
// data/rules/development_score.json) and for deal stages.
import scoreRules from "../../data/rules/development_score.json";

export const SIGNAL_LABELS: Record<string, string> = {
  city_owned_for_sale: "City-owned lot for sale",
  vacant_land: "Vacant land",
  vacant_building_complaint_2y: "Vacant-building complaint, last 2 years",
  open_violations: "Open building violations",
  scofflaw_owner: "Scofflaw owner",
  demolition_notice: "Demolition notice",
};

export const PENALTY_LABELS: Record<string, string> = {
  historic_orange_or_red: "Orange or red historic rating",
  landmark_district: "Landmark district",
  "606_pilsen_surcharge": "606 or Pilsen demolition surcharge",
  fire_limits: "Inside the fire limits",
};

export const INCENTIVE_LABELS: Record<string, string> = {
  ez: "Enterprise Zone",
  oz: "Opportunity Zone",
  tif: "TIF district",
};

type ScoreRules = {
  parts: Record<string, { max: number; rule?: string; points?: Record<string, number>; requires?: { rule: string } }>;
  penalties: { min_total: number; points: Record<string, number> };
};
const rules = scoreRules as unknown as ScoreRules;
const pts = (p: Record<string, number> | undefined, names: Record<string, string>) =>
  Object.entries(p ?? {})
    .map(([k, v]) => `${names[k] ?? k.replace(/_/g, " ")} ${v}`)
    .join(", ");

/** The score's parts, with the rule text read from data/rules/development_score.json (rules live in data). */
export const SCORE_PARTS: { key: "zoning_upside" | "profit" | "acquisition" | "location" | "incentives" | "penalties"; label: string; max: number; how: string }[] = [
  { key: "zoning_upside", label: "Zoning upside", max: rules.parts.zoning_upside.max, how: rules.parts.zoning_upside.rule ?? "" },
  {
    key: "profit",
    label: "Profit",
    max: rules.parts.profit.max,
    how: `${rules.parts.profit.rule ?? ""}. ${rules.parts.profit.requires?.rule ?? ""}`,
  },
  {
    key: "acquisition",
    label: "Acquisition signals",
    max: rules.parts.acquisition_signals.max,
    how: `${pts(rules.parts.acquisition_signals.points, SIGNAL_LABELS)}; capped at ${rules.parts.acquisition_signals.max}`,
  },
  {
    key: "location",
    label: "Location",
    max: rules.parts.location.max,
    how: pts(rules.parts.location.points, { transit_served: "Transit-served", comps_6_plus_within_0_75_mi: "6 or more sale comps within 0.75 mi" }),
  },
  { key: "incentives", label: "Incentives", max: rules.parts.incentives.max, how: rules.parts.incentives.rule ?? "" },
  {
    key: "penalties",
    label: "Penalties",
    max: rules.penalties.min_total,
    how: `${pts(rules.penalties.points, PENALTY_LABELS)}; at most ${rules.penalties.min_total} in all`,
  },
];

export const SCORE_LABEL = "A sorting aid built from the points shown; it does not rate investment quality.";
export const SCORE_SOURCE = "25x125 nightly score (jobs/score_parcels.py), weights in data/rules/development_score.json";

export const STAGES: { id: string; label: string }[] = [
  { id: "lead", label: "Lead" },
  { id: "contacted", label: "Contacted" },
  { id: "feasibility", label: "Feasibility" },
  { id: "under_contract", label: "Under contract" },
  { id: "passed", label: "Passed" },
];

export const EVENT_KINDS: { id: string; label: string }[] = [
  { id: "letter", label: "Letter mailed" },
  { id: "call", label: "Call" },
  { id: "text", label: "Text message" },
  { id: "email", label: "Email" },
  { id: "visit", label: "Site visit" },
  { id: "meeting", label: "Meeting" },
  { id: "note", label: "Note" },
  { id: "reminder", label: "Reminder" },
];

export const OUTREACH_NOTE = "Calls and texts follow TCPA rules; email follows CAN-SPAM.";
