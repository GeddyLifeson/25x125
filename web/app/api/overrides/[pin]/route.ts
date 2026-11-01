// Feasibility edits saved to the organization for one parcel.
import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

async function handle(req: Request, { params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;
  return toEngine(req, `/overrides/${encodeURIComponent(pin.replace(/\D/g, ""))}`);
}

export { handle as GET, handle as PUT, handle as DELETE };
