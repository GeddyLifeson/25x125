// Stripe: checkout and portal (form posts from the account page, answered with a redirect to Stripe),
// and the webhook (Stripe calls it; the raw body and signature go to the engine unchanged).
import { NextResponse } from "next/server";
import { ENGINE_URL } from "../../../../lib/claim";
import { appUrl, claimHeaders } from "../../../../lib/session";

export const dynamic = "force-dynamic";

export async function POST(req: Request, { params }: { params: Promise<{ action: string }> }) {
  const { action } = await params;
  if (action === "webhook") {
    const res = await fetch(`${ENGINE_URL}/billing/webhook`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json", "stripe-signature": req.headers.get("stripe-signature") ?? "" },
      body: await req.text(),
    }).catch(() => null);
    if (!res) return Response.json({ detail: "engine not answering" }, { status: 503 });
    return new Response(await res.text(), { status: res.status, headers: { "content-type": "application/json" } });
  }
  if (action !== "checkout" && action !== "portal") return new Response("unknown billing action", { status: 404 });
  const back = (msg: string) => NextResponse.redirect(new URL(`/account?billing_error=${encodeURIComponent(msg)}`, req.url), 303);
  let res: Response;
  try {
    res = await fetch(`${ENGINE_URL}/billing/${action}`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json", ...(await claimHeaders()) },
      body: JSON.stringify({ base_url: appUrl(req) }),
    });
  } catch {
    return back("The engine is not answering.");
  }
  const body = (await res.json()) as { url?: string; detail?: string };
  if (!res.ok || !body.url) return back(body.detail ?? res.statusText);
  return NextResponse.redirect(body.url, 303);
}
