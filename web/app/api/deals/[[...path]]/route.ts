// Deals and the outreach log (engine/deals.py): every method passes straight through to the engine.
import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path?: string[] }> };

async function handle(req: Request, { params }: Ctx) {
  const { path } = await params;
  const rest = (path ?? []).map(encodeURIComponent).join("/");
  return toEngine(req, `/deals${rest ? `/${rest}` : ""}`);
}

export { handle as GET, handle as POST, handle as PATCH, handle as DELETE };
