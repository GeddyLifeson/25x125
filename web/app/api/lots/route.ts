// The scored list (engine GET /lots), as JSON or CSV (format=csv).
import { toEngine } from "../../../lib/proxy";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  return toEngine(req, "/lots");
}
