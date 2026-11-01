// Pass a browser request through to the engine (or the tile server), so the browser talks only to this app.
import { ENGINE_URL } from "./engine";

export const TILES_URL = process.env.TILES_URL ?? "http://localhost:3100";

const PASS_HEADERS = ["content-type", "content-disposition", "content-encoding", "cache-control"];

export async function proxy(req: Request, base: string, path: string): Promise<Response> {
  const url = new URL(req.url);
  const init: RequestInit = { method: req.method, cache: "no-store", headers: {} };
  const ct = req.headers.get("content-type");
  if (ct) (init.headers as Record<string, string>)["content-type"] = ct;
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.text();
  let res: Response;
  try {
    res = await fetch(`${base}${path}${url.search}`, init);
  } catch {
    return Response.json({ detail: `Not answering at ${base}.` }, { status: 503 });
  }
  const headers = new Headers();
  for (const h of PASS_HEADERS) {
    const v = res.headers.get(h);
    // fetch already decoded gzip bodies, so don't pass the encoding header on.
    if (v && h !== "content-encoding") headers.set(h, v);
  }
  return new Response(res.status === 204 ? null : await res.arrayBuffer(), { status: res.status, headers });
}

export const toEngine = (req: Request, path: string) => proxy(req, ENGINE_URL, path);
