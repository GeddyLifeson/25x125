// Feedback (engine/feedback.py): sending is open to everyone; reading, the summary and the CSV are for
// product admins. /api/feedback/csv maps to the engine's /feedback.csv.
import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path?: string[] }> };

async function handle(req: Request, { params }: Ctx) {
  const { path } = await params;
  const rest = (path ?? []).map(encodeURIComponent).join("/");
  if (rest === "csv") return toEngine(req, "/feedback.csv");
  return toEngine(req, `/feedback${rest ? `/${rest}` : ""}`);
}

export { handle as GET, handle as POST, handle as DELETE };
