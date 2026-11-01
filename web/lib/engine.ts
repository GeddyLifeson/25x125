// Server-side calls to the FastAPI engine. Screens never call the data portals (CLAUDE.md rule 10).
import type { Feasibility, Overrides, Parcel, SaleValue, SearchHit, Zoning } from "./types";

export const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";

export class EngineError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${ENGINE_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new EngineError(503, `The engine is not answering at ${ENGINE_URL}.`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep the status text
    }
    throw new EngineError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const cleanPin = (pin: string) => pin.replace(/\D/g, "");

export function searchParcels(q: string): Promise<SearchHit[]> {
  return call<SearchHit[]>(`/search?q=${encodeURIComponent(q)}&limit=25`);
}

export function getParcel(pin: string): Promise<Parcel> {
  return call<Parcel>(`/parcels/${cleanPin(pin)}`);
}

export function getZoning(pin: string, target?: string | null): Promise<Zoning> {
  const t = target ? `?target=${encodeURIComponent(target)}` : "";
  return call<Zoning>(`/parcels/${cleanPin(pin)}/zoning${t}`);
}

export function getSaleValue(pin: string, units = 3): Promise<SaleValue> {
  return call<SaleValue>(`/parcels/${cleanPin(pin)}/sale-value?units=${units}`);
}

export function postFeasibility(
  pin: string,
  exit: "sell" | "hold",
  target: string | null | undefined,
  overrides: Overrides,
): Promise<Feasibility> {
  const qs = new URLSearchParams({ exit });
  if (target) qs.set("target", target);
  return call<Feasibility>(`/parcels/${cleanPin(pin)}/feasibility?${qs}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(overrides ?? {}),
  });
}

/** Settle a promise into a value or an error message, so one missing piece doesn't blank the page. */
export async function settle<T>(p: Promise<T>): Promise<{ ok: true; value: T } | { ok: false; error: string; status: number }> {
  try {
    return { ok: true, value: await p };
  } catch (e) {
    if (e instanceof EngineError) return { ok: false, error: e.message, status: e.status };
    return { ok: false, error: String(e), status: 500 };
  }
}

export function getCommunityAreas(): Promise<import("./types").CommunityArea[]> {
  return call(`/community-areas`);
}

export function getDeals(): Promise<import("./types").Deal[]> {
  return call(`/deals`);
}

export function getDeal(id: string | number): Promise<import("./types").Deal> {
  return call(`/deals/${encodeURIComponent(String(id))}`);
}
