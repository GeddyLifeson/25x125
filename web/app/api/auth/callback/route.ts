// The link in the sign-in email lands here: trade the one-use token for a session cookie.
import { NextResponse } from "next/server";
import { ENGINE_URL } from "../../../../lib/claim";
import { serviceHeaders, sessionCookie } from "../../../../lib/session";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const token = url.searchParams.get("token") ?? "";
  const fail = (msg: string) => NextResponse.redirect(new URL(`/signin?error=${encodeURIComponent(msg)}`, url), 303);
  if (!token) return fail("The sign-in link is incomplete.");
  let res: Response;
  try {
    res = await fetch(`${ENGINE_URL}/auth/verify`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json", ...(await serviceHeaders()) },
      body: JSON.stringify({ token }),
    });
  } catch {
    return fail("The engine is not answering. Try the link again in a minute.");
  }
  const body = (await res.json()) as { session_token?: string; next?: string; detail?: string };
  if (!res.ok || !body.session_token) return fail(body.detail ?? "That sign-in link did not work.");
  const next = body.next && body.next.startsWith("/") && !body.next.startsWith("//") ? body.next : "/";
  const out = NextResponse.redirect(new URL(next, url), 303);
  out.cookies.set(sessionCookie(body.session_token));
  return out;
}
