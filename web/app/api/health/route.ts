// Health check for the host and the uptime monitor (docs/deploy.md).
// GET /api/health: the engine's /health (database, PostGIS, freshness per source), with its status code:
//   200 with status "ok" or "stale" (a nightly source is over 36 hours old), 503 when the engine or database is down.
// GET /api/health?scope=web: this app alone, always 200 while it runs (the Fly check, so an engine outage
//   doesn't take the web app out of rotation).
import { ENGINE_URL } from "../../../lib/claim";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (new URL(req.url).searchParams.get("scope") === "web") return Response.json({ web: "ok" });
  try {
    const res = await fetch(`${ENGINE_URL}/health`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    const engine = await res.json();
    return Response.json({ web: "ok", ...engine }, { status: res.status, headers: { "cache-control": "no-store" } });
  } catch {
    return Response.json({ web: "ok", status: "degraded", engine: "not answering" }, { status: 503 });
  }
}
