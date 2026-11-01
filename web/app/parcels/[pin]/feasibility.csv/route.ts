// CSV export of every feasibility line, result, incentive, flag and source (CLAUDE.md rule 8).
import { EngineError, checkExport, getParcel, postFeasibility, wallRedirect } from "../../../../lib/engine";
import { titleCase } from "../../../../lib/format";
import { overridesFromParam } from "../../../../lib/overrides";
import { feasibilityCsv } from "../../../../lib/report";

export const dynamic = "force-dynamic";

export async function GET(req: Request, { params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;
  const url = new URL(req.url);
  const exit = url.searchParams.get("exit") === "hold" ? "hold" : "sell";
  const target = url.searchParams.get("target");
  const overrides = overridesFromParam(url.searchParams.get("o"));
  try {
    // Plan check, rate limit and audit row before anything is built.
    await checkExport("feasibility_csv", `PIN ${pin}`);
  } catch (e) {
    const status = e instanceof EngineError ? e.status : 500;
    const back = `/parcels/${pin}/feasibility${url.search}`;
    return wallRedirect(req, status, back) ?? new Response(e instanceof Error ? e.message : String(e), { status });
  }
  try {
    const [f, p] = await Promise.all([postFeasibility(pin, exit, target, overrides), getParcel(pin)]);
    const today = new Date().toISOString().slice(0, 10);
    const body = "﻿" + feasibilityCsv(f, titleCase(p.address) || pin, today);
    return new Response(body, {
      headers: {
        "content-type": "text/csv; charset=utf-8",
        "content-disposition": `attachment; filename="25x125-feasibility-${f.pin}-${exit}-${today}.csv"`,
      },
    });
  } catch (e) {
    const status = e instanceof EngineError ? e.status : 500;
    return new Response(`Could not build the CSV: ${e instanceof Error ? e.message : String(e)}`, { status });
  }
}
