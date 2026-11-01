// Area snapshot line above the list (engine GET /community-areas/{num}/snapshot).
import { toEngine } from "../../../../../lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: Request, { params }: { params: Promise<{ num: string }> }) {
  const { num } = await params;
  return toEngine(req, `/community-areas/${encodeURIComponent(num)}/snapshot`);
}
