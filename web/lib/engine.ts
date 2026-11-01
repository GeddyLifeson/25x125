// Server-side calls to the FastAPI engine. Screens never call the data portals (CLAUDE.md rule 10).
// Every call carries a signed claim with the signed-in user's organization (lib/claim.ts, engine/auth.py).
import { ENGINE_URL } from "./claim";
import { claimHeaders } from "./session";
import type { Feasibility, Overrides, Parcel, SaleValue, SearchHit, Zoning } from "./types";

export { ENGINE_URL };

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
    res = await fetch(`${ENGINE_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers: { ...(init?.headers as Record<string, string> | undefined), ...(await claimHeaders()) },
    });
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

export function getSavedEdits(pin: string): Promise<import("./types").SavedEdits> {
  return call(`/overrides/${cleanPin(pin)}`);
}

/** Before a PDF or CSV is built: the engine checks the plan and the rate limit, and logs the export. */
export function checkExport(kind: "pdf" | "feasibility_csv", target: string): Promise<{ ok: true }> {
  return call(`/exports`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ kind, target }),
  });
}

/** Where to send a browser that hit a sign-in (401) or plan (402) wall on a download link. */
export function wallRedirect(req: Request, status: number, back: string): Response | null {
  const base = new URL(req.url);
  if (status === 401) return Response.redirect(new URL(`/signin?next=${encodeURIComponent(back)}`, base), 303);
  if (status === 402) return Response.redirect(new URL(`/account?need=exports`, base), 303);
  return null;
}

export type AccountView = {
  user: { id: string; email: string };
  org: import("./session").OrgView;
  members: { id: string; email: string; role: string; since: string }[];
  invites: { id: number; email: string; sent: string; expires: string }[];
  plans: PlansFile;
};

export type PlansFile = {
  source: string;
  verified_on: string;
  trial_days: number;
  plans: Record<string, { label: string; price_month: number; founding_price_month?: number; features: string[]; summary: string }>;
  feature_labels: Record<string, string>;
  billing_ready?: boolean;
};

export type AuditRow = { at: string; who: string | null; action: string; target: string | null; detail: Record<string, unknown> };

export function getAccount(): Promise<AccountView> {
  return call(`/account`);
}

export function getBillingPlans(): Promise<PlansFile> {
  return call(`/billing/plans`);
}

export function getAuditLog(limit = 50): Promise<AuditRow[]> {
  return call(`/account/audit?limit=${limit}`);
}

export function getSavedSearches(): Promise<import("./types").SavedSearch[]> {
  return call(`/saved-searches`);
}
