// Shapes of the engine's JSON responses (engine/app.py). Checked against live responses on 2026-11-01.

export type SearchHit = {
  pin: string;
  address: string | null;
  zip: string | null;
  zone_class: string | null;
  lot_sqft: number | null;
};

export type Signal = {
  kind: string;
  date: string | null;
  status: string | null;
  detail: string | null;
  match: string | null;
};

export type Parcel = {
  pin: string;
  pin10: string;
  address: string | null;
  zip: string | null;
  class: string | null;
  ward: number | null;
  community_area: string | null;
  nbhd_code: string | null;
  tract: string | null;
  lat: number | null;
  lon: number | null;
  tax_year: number | null;
  zone_class: string | null;
  zone_share: number | null;
  zone_class_2: string | null;
  zone_share_2: number | null;
  lot_sqft: number | null;
  frontage_ft: number | null;
  depth_ft: number | null;
  lot_source: string | null;
  historic_rating: string | null;
  landmark_name: string | null;
  tif_name: string | null;
  cta_rail_ft: number | null;
  metra_ft: number | null;
  transit_served: string | null;
  adu_zone: string | null;
  special_district: string | null;
  aro_area: string | null;
  pedestrian_street: string | null;
  enterprise_zone: string | null;
  opportunity_zone_2018: string | boolean | null;
  fire_limits: boolean | null;
  open_violations: number | null;
  last_violation_date: string | null;
  vacant_building_311: string | null;
  vacant_lot_311: string | null;
  scofflaw: boolean | string | null;
  city_owned_status: string | null;
  demolition_notice_date: string | null;
  foreclosures_half_mile_5y: number | null;
  nearest_new_construction_ft: number | null;
  stories: number | null;
  footprint_units: number | null;
  hearing_fines_3y: number | null;
  vacant_building_fine_due: number | null;
  environmental_hold: string | boolean | null;
  foreclosed_rental_date: string | null;
  exempt_owner: string | null;
  use_now: string | null;
  units_now: number | null;
  block_face_lots: number | null;
  block_face_multi_lots: number | null;
  pulled_at: string | null;
  recent_sales: { date: string; price: number; deed_type: string | null }[];
  signals: Signal[];
  sources: Record<string, string>;
};

export type ZoningPath = {
  id: string;
  name: string;
  approval: string;
  district: string;
  units: number;
  floor_area_sqft: number | null;
  max_height_ft: number | null;
  parking_spaces: number | null;
  bike_spaces?: number | null;
  notes: string[];
  citations: string[];
};

export type ZoningFlag = { id: string; text: string; citation: string | null; dollars?: number | null };

export type Zoning = {
  pin: string;
  zone_class: string;
  covered: boolean;
  lot_sqft: number | null;
  frontage_ft: number | null;
  paths: ZoningPath[];
  flags: ZoningFlag[];
};

export type Comp = {
  pin: string;
  kind: string;
  sale_date: string;
  price_per_unit: number;
  adjusted: number;
  weight: number;
};

export type SaleValue = {
  per_unit: number;
  low: number | null;
  high: number | null;
  range: string;
  comps: number;
  radius_mi: number;
  same_size_group: boolean;
  notes: string[];
  time_index: Record<string, number>;
  source: string;
  label: string;
  comp_list: Comp[];
};

export type CostLine = { id: string; name: string; basis: string; value: number; low: number; high: number };

export type Incentive = {
  id: string;
  name: string;
  applies: boolean;
  on: boolean;
  value: number;
  basis: string;
  kind: "cash" | "deferral" | "tax" | "flag" | string;
  note: string | null;
};

export type SellBlock = {
  sale_per_unit: number;
  sale_total: number;
  net_sale: number;
  net_sale_basis: string;
  sale_range: { low: number; high: number; label: string; comps: number } | null;
  profit: number;
  return_on_cost: number;
  margin_on_net_sale: number;
  max_land_price: number;
  target_return_on_cost: number;
  max_land_price_at: Record<string, number>;
  reference_lines: { return_on_cost: number[]; label: string };
  range: {
    p10: number;
    p25: number;
    p50: number;
    p90: number;
    loss_share: number;
    draws: number;
    seed: number;
    sale_cost_correlation: number;
    label: string;
  } | null;
  stress_case: { profit: number; label: string } | null;
};

export type HoldBlock = {
  rent_per_unit: number;
  effective_gross_income: number;
  operating_costs_before_tax: number;
  property_tax: number;
  noi: number;
  value: number;
  value_basis: string;
  yield_on_cost: number;
  equity_created: number;
  spread_over_cap_rate_pts: number;
  loan_at_dscr: number;
  loan_at_dscr_basis: string;
  refinance_gap: number;
  reference_lines: { spread_over_cap_rate_pts: number; dscr: number; label: string };
  rent_range: { low: number; high: number } | null;
};

export type Scenario = {
  name: string;
  approval: string;
  units: number;
  exit: "sell" | "hold";
  gross_sqft: number;
  unit_sqft: number;
  cost: {
    gfa_sqft: number;
    preset: string;
    base_per_sqft: number;
    adjustment: number;
    land: number;
    hard: number;
    total: number;
    finance_share: number;
    low: number;
    high: number;
    stage: string;
    [k: string]: number | string;
  };
  lines: CostLine[];
  cost_range: { central: number; low: number; high: number; low_margin: number; high_margin: number; label: string };
  cost_per_unit: number;
  sell?: SellBlock;
  hold?: HoldBlock;
  incentives: Incentive[];
  incentive_total: number;
  flags: { tag: string; text: string }[];
  buyer_financing: { class: string; fha_limit?: number; over_fha_limit?: boolean } | null;
  path: Omit<ZoningPath, "name" | "approval" | "bike_spaces">;
  pattern: string | null;
  sale_source: {
    comps: number;
    radius_mi: number;
    same_size_group: boolean;
    notes: string[];
    sell_as: string;
    time_index: Record<string, number>;
    source: string;
  } | null;
  rent_source: {
    per_month: number;
    low: number;
    high: number;
    acs_median: number;
    acs_moe: number;
    acs_source: string;
    growth_since_acs: number;
    factor: number;
    range: string;
  } | null;
};

export type Feasibility = {
  pin: string;
  address_area: string | null;
  zone_class: string;
  lot_sqft: number | null;
  frontage_ft: number | null;
  exit: "sell" | "hold";
  zoning_flags: ZoningFlag[];
  inputs: {
    cost_index: {
      index: number;
      thin: boolean;
      permits: number;
      neighbor_weight: number;
      computed_on: string;
    } | null;
    land_value: {
      geo: string;
      geo_id: string;
      sales: number;
      per_lot_sqft: number;
      per_buildable_sqft: number | null;
      first_sale: string;
      last_sale: string;
      source: string;
    } | null;
    escalation: { factor: number; latest_month: string; change_12m: number; basis: string } | null;
  };
  scenarios: Scenario[];
  label: string;
  patterns_checked: { pattern: string; path: string; fits: boolean; why: string }[];
};

/** Per-deal edits sent to the engine: {"all": {...}, "0": {...}, "1": {...}, "2": {...}}. */
export type ScenarioOverrides = {
  units?: number;
  unit_sqft?: number;
  gross_sqft?: number;
  land?: number;
  sale_per_unit?: number;
  rent_per_unit?: number;
  cost_index?: number;
  preset?: string;
  stage?: string;
  sell_as?: string;
  escalation?: number;
  toggles?: Record<string, boolean>;
  answers?: Record<string, boolean | number>;
};
export type Overrides = Record<string, ScenarioOverrides>;

/** One row of GET /lots (engine/parcels.py LOT_COLUMNS): a scored lot with its points by part. */
export type Lot = {
  pin10: string;
  pin: string;
  address: string | null;
  zip: string | null;
  community_area: string | null;
  zone_class: string | null;
  lot_sqft: number | null;
  score: number;
  zoning_upside: number;
  profit: number;
  acquisition: number;
  location: number;
  incentives: number;
  penalties: number;
  units_now: number | null;
  by_right_units: number | null;
  units_priced: number | null;
  sale_per_unit: number | null;
  sale_comps: number | null;
  land: number | null;
  total_cost: number | null;
  profit_central: number | null;
  profit_p25: number | null;
  return_on_cost: number | null;
  return_on_cost_p25: number | null;
  max_land_price: number | null;
  details: {
    signals?: string[];
    penalties?: string[];
    incentives?: string[];
    fast_path?: boolean;
    profit?: string;
    sale_ring?: number;
    comps_within_0_75_mi?: number;
    priced_units?: number;
  };
  computed_on: string;
  lat: number | null;
  lon: number | null;
};

export type CommunityArea = { num: number; name: string; bounds: [number, number, number, number] };

export type AreaSnapshot = {
  num: number;
  name: string;
  sales: { kind: string; sales: number; median_per_unit: number; first_sale: string; last_sale: string; computed_on: string }[];
  sales_source: string;
  cost_index: { index: number; permits: number; thin: boolean; computed_on: string; source: string } | null;
  land_value: { per_lot_sqft: number; sales: number; first_sale: string | null; last_sale: string | null; computed_on: string; source: string } | null;
};

export type DealStage = "lead" | "contacted" | "feasibility" | "under_contract" | "passed";

export type DealEvent = { id: number; kind: string; kind_label: string; event_on: string; note: string; created_at: string };

export type Deal = {
  id: number;
  org_id: string | null;
  pin: string;
  pin10: string;
  address: string | null;
  stage: DealStage;
  stage_label: string;
  next_step: string | null;
  next_step_on: string | null;
  exit: "sell" | "hold" | null;
  target: string | null;
  scenario: number | null;
  scenario_name: string | null;
  overrides: Overrides;
  result: {
    scenario: number;
    name: string;
    units: number;
    exit: string;
    total_cost: number;
    total_cost_low: number;
    total_cost_high: number;
    profit?: number;
    profit_p10?: number | null;
    profit_p90?: number | null;
    return_on_cost?: number;
    max_land_price?: number;
    noi?: number;
    yield_on_cost?: number;
    run_on: string;
    source: string;
  } | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  community_area: string | null;
  zone_class: string | null;
  lot_sqft: number | null;
  nightly: {
    score: number;
    by_right_units: number | null;
    profit_central: number | null;
    max_land_price: number | null;
    return_on_cost_p25: number | null;
    computed_on: string;
    source: string;
  } | null;
  events?: DealEvent[];
  outreach_note?: string;
};
