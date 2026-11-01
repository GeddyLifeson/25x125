// Proxy for the feasibility POST, so the browser talks only to this app (no CORS on the engine).
import { NextResponse } from "next/server";
import { EngineError, postFeasibility } from "../../../../../lib/engine";
import type { Overrides } from "../../../../../lib/types";

export const dynamic = "force-dynamic";

export async function POST(req: Request, { params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;
  const url = new URL(req.url);
  const exit = url.searchParams.get("exit") === "hold" ? "hold" : "sell";
  const target = url.searchParams.get("target");
  let overrides: Overrides = {};
  try {
    const body = (await req.json()) as unknown;
    if (body && typeof body === "object" && !Array.isArray(body)) overrides = body as Overrides;
  } catch {
    // empty body: defaults only
  }
  try {
    return NextResponse.json(await postFeasibility(pin, exit, target, overrides));
  } catch (e) {
    const status = e instanceof EngineError ? e.status : 500;
    return NextResponse.json({ detail: e instanceof Error ? e.message : String(e) }, { status });
  }
}
