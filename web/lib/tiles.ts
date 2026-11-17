// Map tiles are fetched gzipped and unpacked here. The app server cannot send content-encoding from a route
// (Next.js drops it), and an uncompressed lot tile is about 4 times larger, which shows on a slow link.
const PREFIX = "x25tile://";

/** Rewrites this app's tile addresses to the x25tile scheme (MapLibre transformRequest). Other requests pass. */
export function tileRequest(url: string, origin: string): { url: string } {
  if (typeof DecompressionStream === "undefined") return { url }; // old browser: plain tiles
  const path = url.startsWith(origin) ? url.slice(origin.length) : url;
  return path.startsWith("/tiles/") ? { url: PREFIX + path.slice(1) } : { url };
}

/** MapLibre protocol handler for x25tile:// addresses: fetch with ?gz=1 and gunzip. */
export async function loadTile(params: { url: string }, abort: AbortController): Promise<{ data: ArrayBuffer; cacheControl?: string | null }> {
  const res = await fetch(`/${params.url.slice(PREFIX.length)}?gz=1`, { signal: abort.signal });
  if (res.status === 204) return { data: new ArrayBuffer(0) };
  if (!res.ok) throw new Error(`tile ${params.url}: ${res.status}`);
  const packed = res.headers.get("x-tile-encoding") === "gzip" && res.body;
  const data = packed
    ? await new Response(res.body!.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer()
    : await res.arrayBuffer();
  return { data, cacheControl: res.headers.get("cache-control") };
}

export const TILE_SCHEME = "x25tile";
