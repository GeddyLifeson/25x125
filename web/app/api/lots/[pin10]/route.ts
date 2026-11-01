// One scored lot (engine GET /lots/{pin10}), for the map's side panel.
import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: Request, { params }: { params: Promise<{ pin10: string }> }) {
  const { pin10 } = await params;
  return toEngine(req, `/lots/${encodeURIComponent(pin10)}`);
}
