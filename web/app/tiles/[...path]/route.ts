// Vector tiles from the Martin tile server (docker compose service "tiles"), passed through so the
// browser loads everything from this app. Set TILES_URL if Martin is not at http://localhost:3100.
import { gzipSync } from "node:zlib";
import { TILES_URL, proxy } from "../../../lib/proxy";

export const dynamic = "force-dynamic";

const LAYERS = new Set(["lots", "land_value", "lots_for_sale"]);

export async function GET(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const [layer, z, x, y] = path;
  if (!LAYERS.has(layer) || ![z, x, y].every((v) => /^\d+$/.test(v ?? ""))) {
    return new Response("unknown tile", { status: 404 });
  }
  const res = await proxy(req, TILES_URL, `/${layer}/${z}/${x}/${y}`);
  const headers = new Headers(res.headers);
  headers.set("content-type", "application/x-protobuf");
  if (!res.ok || res.status === 204) return new Response(res.status === 204 ? null : res.body, { status: res.status, headers });
  // Tiles change once a night, after the score run.
  headers.set("cache-control", "public, max-age=3600");
  let body = new Uint8Array(await res.arrayBuffer());
  // The app server does not compress protobuf on its own; a lot tile shrinks about 3 times with gzip.
  if (/\bgzip\b/.test(req.headers.get("accept-encoding") ?? "")) {
    body = new Uint8Array(gzipSync(body, { level: 4 }));
    headers.set("content-encoding", "gzip");
    headers.set("vary", "accept-encoding");
  }
  return new Response(body, { status: 200, headers });
}
