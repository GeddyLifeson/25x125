// Account, members, invites and the audit log (engine/accounts.py). Deleting the account also clears the cookie.
import { NextResponse } from "next/server";
import { toEngine } from "../../../../lib/proxy";
import { SESSION_COOKIE, appUrl } from "../../../../lib/session";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path?: string[] }> };

async function handle(req: Request, { params }: Ctx) {
  const { path } = await params;
  const rest = (path ?? []).map(encodeURIComponent).join("/");
  let forward = req;
  // Invite emails link back to this app: add its address to the body.
  if (req.method === "POST" && rest === "invites") {
    const body = (await req.json()) as Record<string, unknown>;
    forward = new Request(req.url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...body, base_url: appUrl(req) }),
    });
  }
  const res = await toEngine(forward, `/account${rest ? `/${rest}` : ""}`);
  if (req.method === "DELETE" && !rest && res.ok) {
    const out = new NextResponse(res.body, { status: res.status, headers: res.headers });
    out.cookies.delete(SESSION_COOKIE);
    return out;
  }
  return res;
}

export { handle as GET, handle as POST, handle as PATCH, handle as DELETE };
