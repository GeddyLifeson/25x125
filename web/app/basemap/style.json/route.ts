// The map's background style, drawn from the local Chicago basemap file the engine serves (jobs/build_basemap.py).
// 404 when the engine has no file, and the map then uses the outside basemap (MapScreen.tsx).
// URLs are relative: behind the Codespaces port forwarder the browser's address differs from the Host header,
// so the map makes them absolute with its own window.location.origin.
import { layers, namedFlavor } from "@protomaps/basemaps";
import { ENGINE_URL } from "../../../lib/claim";

export const dynamic = "force-dynamic";

type Info = { min_zoom: number; max_zoom: number; bounds: [number, number, number, number]; attribution: string };

export async function GET() {
  let info: Info;
  try {
    const res = await fetch(`${ENGINE_URL}/basemap`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (!res.ok) return Response.json({ detail: "no local basemap" }, { status: 404 });
    info = (await res.json()) as Info;
  } catch {
    return Response.json({ detail: "engine not answering" }, { status: 404 });
  }
  const style = {
    version: 8,
    glyphs: "/basemap/fonts/{fontstack}/{range}.pbf",
    sprite: "/basemap/sprites/light",
    sources: {
      protomaps: {
        type: "vector",
        tiles: ["/tiles/basemap/{z}/{x}/{y}"],
        minzoom: info.min_zoom,
        maxzoom: info.max_zoom,
        bounds: info.bounds,
        attribution: info.attribution,
      },
    },
    layers: layers("protomaps", namedFlavor("light"), { lang: "en" }),
  };
  return Response.json(style, { headers: { "cache-control": "public, max-age=3600" } });
}
