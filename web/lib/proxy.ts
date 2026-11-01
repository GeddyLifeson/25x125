// Pass a browser request through to the engine (or the tile server), so the browser talks only to this app.
import { ENGINE_URL } from "./claim";
import { claimHeaders } from "./session";

export const TILES_URL = process.env.TILES_URL ?? "http://localhost:3100";

const PASS_HEADERS = ["content-type", "content-disposition", "content-encoding", "cache-control"];

export async function proxy(req: Request, base: string, path: string): Promise<Response> {
  const url = new URL(req.url);
  // The engine only trusts the signed claim; tile requests don't need one.
  const init: RequestInit = { method: req.method, cache: "no-store", headers: base === ENGINE_URL ? await claimHeaders() : {} };
  const ct = req.headers.get("content-type");
  if (ct) (init.headers as Record<string, string>)["content-type"] = ct;
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.text();
  let res: Response;
  try {
    res = await fetch(`${base}${path}${url.search}`, init);
  } catch {
    return Response.json({ detail: `Not answering at ${base}.` }, { status: 503 });
  }
  // A download link opened while signed out (or on Free): send the browser to sign in or to the plans.
  if (req.headers.get("sec-fetch-mode") === "navigate" && (res.status === 401 || res.status === 402)) {
    const back = new URL(req.headers.get("referer") ?? "/", url).pathname;
    const to = res.status === 401 ? `/signin?next=${encodeURIComponent(back)}` : "/account?need=exports";
    return Response.redirect(new URL(to, url), 303);
  }
  const headers = new Headers(res.headers.has("retry-after") ? { "retry-after": res.headers.get("retry-after")! } : undefined);
  for (const h of PASS_HEADERS) {
    const v = res.headers.get(h);
    // fetch already decoded gzip bodies, so don't pass the encoding header on.
    if (v && h !== "content-encoding") headers.set(h, v);
  }
  return new Response(res.status === 204 ? null : await res.arrayBuffer(), { status: res.status, headers });
}

export const toEngine = (req: Request, path: string) => proxy(req, ENGINE_URL, path);
