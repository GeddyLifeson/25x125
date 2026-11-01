// The signed-in user, read from the session cookie through the engine (server side only).
import { cookies, headers } from "next/headers";
import { cache } from "react";
import { CLAIM_HEADER, ENGINE_URL, isProduction, signClaim } from "./claim";

export const SESSION_COOKIE = "x25_session";
export const SESSION_DAYS = 30;

export type OrgView = {
  id: string;
  name: string;
  role: "owner" | "member";
  plan: "free" | "pro";
  plan_label: string;
  plan_status: string;
  trial_ends_at: string | null;
  founding: boolean;
  current_period_end: string | null;
  has_billing: boolean;
  features: string[];
};

export type Session = {
  user: { id: string; email: string; name: string | null };
  /** Product admin (ADMIN_EMAILS on the engine): sees /admin/feedback. */
  is_admin?: boolean;
  org: OrgView;
  orgs: { id: string; name: string; role: string }[];
  expires_at: string;
};

/** Client address for rate limits when signed out. Behind a host's proxy, x-real-ip / x-forwarded-for carry it. */
export async function clientIp(): Promise<string> {
  try {
    const h = await headers();
    return h.get("x-real-ip") ?? h.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  } catch {
    return "unknown";
  }
}

/** A signed claim with no user, for the sign-in routes. */
export async function serviceHeaders(): Promise<Record<string, string>> {
  return { [CLAIM_HEADER]: signClaim({ uid: null, org: null, ip: await clientIp() }) };
}

async function readToken(): Promise<string | null> {
  try {
    return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
  } catch {
    return null; // outside a request
  }
}

export const getSession = cache(async (): Promise<Session | null> => {
  const token = await readToken();
  if (!token) return null;
  try {
    const res = await fetch(`${ENGINE_URL}/auth/session`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json", ...(await serviceHeaders()) },
      body: JSON.stringify({ session_token: token }),
    });
    return res.ok ? ((await res.json()) as Session) : null;
  } catch {
    return null;
  }
});

/** The claim header for the signed-in user's organization (or an anonymous one). */
export async function claimHeaders(): Promise<Record<string, string>> {
  const s = await getSession();
  return { [CLAIM_HEADER]: signClaim({ uid: s?.user.id ?? null, org: s?.org.id ?? null, ip: await clientIp() }) };
}

/** The web app's own address for links in emails and Stripe return pages. Set APP_URL in production. */
export function appUrl(req: Request): string {
  if (process.env.APP_URL) return process.env.APP_URL.replace(/\/$/, "");
  if (isProduction()) throw new Error("APP_URL is not set on the web app");
  return new URL(req.url).origin;
}

export function sessionCookie(token: string) {
  return {
    name: SESSION_COOKIE,
    value: token,
    httpOnly: true,
    sameSite: "lax" as const,
    secure: isProduction(),
    path: "/",
    maxAge: SESSION_DAYS * 24 * 3600,
  };
}

export function trialDaysLeft(org: OrgView): number | null {
  if (org.plan_status !== "trialing" || !org.trial_ends_at) return null;
  return Math.max(0, Math.ceil((Date.parse(org.trial_ends_at) - Date.now()) / 86_400_000));
}
