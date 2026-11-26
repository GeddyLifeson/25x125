// Feasibility edits saved to the organization for one parcel.
import { cleanPin } from "../../../../lib/engine";
import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

async function handle(req: Request, { params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;
  return toEngine(req, `/overrides/${cleanPin(pin)}`);
}

export { handle as GET, handle as PUT, handle as DELETE };
