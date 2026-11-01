// Ask the engine to email a sign-in link. In dev mode (no EMAIL_SERVER on the engine) the link goes to the
// engine console and to .dev-mail/ in the repo root.
import { ENGINE_URL } from "../../../../lib/claim";
import { appUrl, serviceHeaders } from "../../../../lib/session";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  let body: { email?: string; next?: string } = {};
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ detail: "Send JSON with an email." }, { status: 400 });
  }
  let res: Response;
  try {
    res = await fetch(`${ENGINE_URL}/auth/email-link`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json", ...(await serviceHeaders()) },
      body: JSON.stringify({ email: body.email ?? "", next: body.next ?? "/", base_url: appUrl(req) }),
    });
  } catch {
    return Response.json({ detail: `The engine is not answering at ${ENGINE_URL}.` }, { status: 503 });
  }
  return new Response(await res.text(), { status: res.status, headers: { "content-type": "application/json" } });
}
