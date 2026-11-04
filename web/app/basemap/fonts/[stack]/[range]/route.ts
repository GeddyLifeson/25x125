// Label glyphs for the local basemap, from web/basemap-assets/fonts (Noto Sans, SIL Open Font License).
// Only the ranges Chicago's labels use are kept; any other range answers empty, so the map skips those
// characters instead of logging an error.
import { readFile } from "node:fs/promises";
import path from "node:path";

const STACKS = new Set(["Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic"]);
const DIR = path.join(process.cwd(), "basemap-assets", "fonts");

export async function GET(_req: Request, { params }: { params: Promise<{ stack: string; range: string }> }) {
  const { stack, range } = await params;
  const name = decodeURIComponent(stack).split(",").map((s) => s.trim()).find((s) => STACKS.has(s));
  const m = /^(\d+)-(\d+)\.pbf$/.exec(range);
  const headers = { "content-type": "application/x-protobuf", "cache-control": "public, max-age=604800" };
  if (!name || !m) return new Response(new Uint8Array(0), { headers });
  try {
    const body = await readFile(path.join(DIR, name, `${m[1]}-${m[2]}.pbf`));
    return new Response(new Uint8Array(body), { headers });
  } catch {
    return new Response(new Uint8Array(0), { headers });
  }
}
