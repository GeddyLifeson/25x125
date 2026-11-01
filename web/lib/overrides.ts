// Per-deal overrides: parse and write the simple CSV file (CLAUDE.md rules 7 and 8), and pass them in URLs.
import type { Overrides, ScenarioOverrides } from "./types";

export const NUMBER_FIELDS = [
  "units",
  "unit_sqft",
  "gross_sqft",
  "land",
  "sale_per_unit",
  "rent_per_unit",
  "cost_index",
  "escalation",
] as const;
export const TEXT_FIELDS = ["preset", "stage", "sell_as"] as const;
export const TEXT_CHOICES: Record<(typeof TEXT_FIELDS)[number], string[]> = {
  preset: ["production", "standard", "high"],
  stage: ["feasibility", "layout", "drawings", "bids"],
  sell_as: ["building", "condo"],
};

const SCENARIO_KEYS: Record<string, string> = { all: "all", "": "all", a: "0", b: "1", c: "2", "0": "0", "1": "1", "2": "2" };

/** Split one CSV line, honoring double quotes. */
export function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (q) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') q = false;
      else cur += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else cur += ch;
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

export function csvCell(v: unknown): string {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function parseBool(v: string): boolean | null {
  const s = v.toLowerCase();
  if (["on", "yes", "true", "1", "y"].includes(s)) return true;
  if (["off", "no", "false", "0", "n"].includes(s)) return false;
  return null;
}

/**
 * Read an overrides file. Either `field,value` (applies to every scenario) or `scenario,field,value`
 * with scenario all, A, B or C. Fields: units, unit_sqft, gross_sqft, land, sale_per_unit, rent_per_unit,
 * cost_index, escalation, preset, stage, sell_as, toggle.<incentive id>, answer.<question id>.
 */
export function parseOverridesCsv(text: string): { overrides: Overrides; errors: string[]; count: number } {
  const overrides: Overrides = {};
  const errors: string[] = [];
  let count = 0;
  const lines = text.replace(/^﻿/, "").split(/\r?\n/);
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    let cells = splitCsvLine(line);
    if (cells.length === 2) cells = ["all", ...cells];
    if (cells.length < 3) {
      errors.push(`Line ${i + 1}: expected field,value or scenario,field,value`);
      return;
    }
    const [scRaw, field, value] = cells;
    if (i === 0 && /^(scenario|field)$/i.test(scRaw === "all" ? field : scRaw)) return; // header
    const sc = SCENARIO_KEYS[scRaw.toLowerCase()];
    if (!sc) {
      errors.push(`Line ${i + 1}: scenario must be all, A, B or C (got "${scRaw}")`);
      return;
    }
    if (value === "") return;
    const target: ScenarioOverrides = (overrides[sc] ??= {});
    if ((NUMBER_FIELDS as readonly string[]).includes(field)) {
      const n = Number(value.replace(/[$,\s]/g, ""));
      if (!Number.isFinite(n)) {
        errors.push(`Line ${i + 1}: ${field} must be a number (got "${value}")`);
        return;
      }
      (target as Record<string, unknown>)[field] = n;
    } else if ((TEXT_FIELDS as readonly string[]).includes(field)) {
      const f = field as (typeof TEXT_FIELDS)[number];
      if (!TEXT_CHOICES[f].includes(value.toLowerCase())) {
        errors.push(`Line ${i + 1}: ${field} must be one of ${TEXT_CHOICES[f].join(", ")}`);
        return;
      }
      (target as Record<string, unknown>)[field] = value.toLowerCase();
    } else if (field.startsWith("toggle.")) {
      const b = parseBool(value);
      if (b === null) {
        errors.push(`Line ${i + 1}: ${field} must be on or off`);
        return;
      }
      (target.toggles ??= {})[field.slice(7)] = b;
    } else if (field.startsWith("answer.")) {
      const n = Number(value);
      const b = parseBool(value);
      if (!Number.isFinite(n) && b === null) {
        errors.push(`Line ${i + 1}: ${field} must be yes, no or a number`);
        return;
      }
      (target.answers ??= {})[field.slice(7)] = Number.isFinite(n) ? n : (b as boolean);
    } else {
      errors.push(`Line ${i + 1}: unknown field "${field}"`);
      return;
    }
    count++;
  });
  return { overrides, errors, count };
}

export function overridesToCsv(o: Overrides): string {
  const rows = ["scenario,field,value"];
  const name = (k: string) => (k === "all" ? "all" : "ABC"[Number(k)] ?? k);
  for (const k of Object.keys(o).sort()) {
    const s = o[k];
    for (const [f, v] of Object.entries(s)) {
      if (f === "toggles" || f === "answers") {
        for (const [id, b] of Object.entries(v as Record<string, unknown>)) {
          const val = typeof b === "boolean" ? (f === "toggles" ? (b ? "on" : "off") : b ? "yes" : "no") : b;
          rows.push([name(k), `${f === "toggles" ? "toggle" : "answer"}.${id}`, val].map(csvCell).join(","));
        }
      } else rows.push([name(k), f, v].map(csvCell).join(","));
    }
  }
  return rows.join("\r\n") + "\r\n";
}

/** Merge b into a, scenario by scenario; toggles and answers merge key by key. */
export function mergeOverrides(a: Overrides, b: Overrides): Overrides {
  const out: Overrides = JSON.parse(JSON.stringify(a));
  for (const [k, s] of Object.entries(b)) {
    const t = (out[k] ??= {});
    for (const [f, v] of Object.entries(s)) {
      if (f === "toggles" || f === "answers") {
        (t as Record<string, unknown>)[f] = { ...((t as Record<string, Record<string, unknown>>)[f] ?? {}), ...(v as object) };
      } else (t as Record<string, unknown>)[f] = v;
    }
  }
  return out;
}

/** Overrides from the `o` query parameter (JSON), as used by the PDF and CSV links. */
export function overridesFromParam(raw: string | null | undefined): Overrides {
  if (!raw) return {};
  try {
    const v = JSON.parse(raw) as unknown;
    return v && typeof v === "object" && !Array.isArray(v) ? (v as Overrides) : {};
  } catch {
    return {};
  }
}
