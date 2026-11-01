import { toEngine } from "../../../../lib/proxy";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path?: string[] }> };

async function handle(req: Request, { params }: Ctx) {
  const { path } = await params;
  const rest = (path ?? []).map(encodeURIComponent).join("/");
  return toEngine(req, `/saved-searches${rest ? `/${rest}` : ""}`);
}

export { handle as GET, handle as POST, handle as DELETE };
