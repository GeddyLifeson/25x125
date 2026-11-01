import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ENGINE_URL } from "../../../../lib/claim";
import { SESSION_COOKIE, serviceHeaders } from "../../../../lib/session";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) {
    try {
      await fetch(`${ENGINE_URL}/auth/signout`, {
        method: "POST",
        cache: "no-store",
        headers: { "content-type": "application/json", ...(await serviceHeaders()) },
        body: JSON.stringify({ session_token: token }),
      });
    } catch {
      // the cookie goes either way
    }
  }
  const out = NextResponse.redirect(new URL("/", req.url), 303);
  out.cookies.delete(SESSION_COOKIE);
  return out;
}
