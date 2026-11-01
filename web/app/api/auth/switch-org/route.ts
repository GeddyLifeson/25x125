import { cookies } from "next/headers";
import { ENGINE_URL } from "../../../../lib/claim";
import { SESSION_COOKIE, serviceHeaders } from "../../../../lib/session";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return Response.json({ detail: "Sign in first." }, { status: 401 });
  const { org_id } = (await req.json()) as { org_id?: string };
  const res = await fetch(`${ENGINE_URL}/auth/switch-org`, {
    method: "POST",
    cache: "no-store",
    headers: { "content-type": "application/json", ...(await serviceHeaders()) },
    body: JSON.stringify({ session_token: token, org_id: org_id ?? "" }),
  });
  return new Response(await res.text(), { status: res.status, headers: { "content-type": "application/json" } });
}
