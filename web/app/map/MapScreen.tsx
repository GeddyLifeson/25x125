"use client";
import "maplibre-gl/dist/maplibre-gl.css";
import Link from "next/link";
import type { ExpressionSpecification, FilterSpecification, Map as MLMap, Marker, StyleSpecification } from "maplibre-gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SaveSearch } from "../../components/SaveSearch";
import { LotPanel } from "../../components/LotPanel";
import { Source } from "../../components/Source";
import { num, pct, titleCase, usd, usdK } from "../../lib/format";
import { PENALTY_LABELS, SCORE_LABEL, SIGNAL_LABELS } from "../../lib/labels";
import type { AreaSnapshot, CommunityArea, Lot } from "../../lib/types";

export type Filters = {
  community_area: string;
  zone: string;
  min_score: string;
  min_units: string;
  signal: string;
  for_sale: boolean;
  vacant: boolean;
  fast_path: boolean;
  sort: string;
};

export const DEFAULT_FILTERS: Filters = {
  community_area: "",
  zone: "",
  min_score: "",
  min_units: "",
  signal: "",
  for_sale: false,
  vacant: false,
  fast_path: false,
  sort: "score",
};

const PAGE = 50;
const BASEMAP = process.env.NEXT_PUBLIC_BASEMAP_STYLE ?? "https://tiles.openfreemap.org/styles/positron";
const CHICAGO: [number, number, number, number] = [-87.94, 41.645, -87.524, 42.023];

// Score colours: one hue, light to dark (sequential), so a higher score reads darker.
export const SCORE_STEPS: { from: number; color: string }[] = [
  { from: 0, color: "#dfe3e8" },
  { from: 20, color: "#b3d1ea" },
  { from: 40, color: "#6aa9dd" },
  { from: 60, color: "#1c6db0" },
  { from: 80, color: "#0b3a63" },
];
// Land value colours: a second single hue, so the two layers never read as one scale.
const LAND_STEPS: { from: number; color: string }[] = [
  { from: 0, color: "#fdebd3" },
  { from: 10, color: "#f8c58c" },
  { from: 25, color: "#ee9a4d" },
  { from: 50, color: "#c96a1b" },
  { from: 100, color: "#8a4600" },
];
const SALE_COLORS = { city: "#7a3e00", land_bank: "#4b3a7a" };

const stepExpr = (prop: string, steps: { from: number; color: string }[]): ExpressionSpecification =>
  ["step", ["coalesce", ["get", prop], 0], steps[0].color, ...steps.slice(1).flatMap((s) => [s.from, s.color])] as unknown as ExpressionSpecification;

const SORTS: { id: string; label: string }[] = [
  { id: "score", label: "Development score" },
  { id: "return", label: "Return on cost (25th percentile)" },
  { id: "upside", label: "Extra units by right" },
  { id: "lot", label: "Lot size" },
];
const SIGNAL_CHOICES = ["vacant_building_complaint_2y", "open_violations", "scofflaw_owner", "demolition_notice"];

function lotsQuery(f: Filters, offset: number, format?: "csv"): string {
  const qs = new URLSearchParams();
  if (f.community_area) qs.set("community_area", f.community_area);
  if (f.zone.trim()) qs.set("zone", f.zone.trim().toUpperCase());
  if (f.min_score) qs.set("min_score", f.min_score);
  if (f.min_units) qs.set("min_units", f.min_units);
  if (f.signal) qs.set("signal", f.signal);
  if (f.for_sale) qs.set("for_sale", "true");
  if (f.vacant) qs.set("vacant", "true");
  if (f.fast_path) qs.set("fast_path", "true");
  qs.set("sort", f.sort);
  if (format) {
    qs.set("format", format);
    qs.set("limit", "5000");
  } else {
    qs.set("limit", String(PAGE));
    qs.set("offset", String(offset));
  }
  return qs.toString();
}

/** The same filters as the list, as a map filter on the tile properties, so map and list agree. */
function mapFilter(f: Filters): FilterSpecification {
  const all: unknown[] = ["all"];
  if (f.min_score) all.push([">=", ["coalesce", ["get", "score"], 0], Number(f.min_score)]);
  if (f.min_units) all.push([">=", ["coalesce", ["get", "units"], 0], Number(f.min_units)]);
  if (f.community_area) all.push(["==", ["get", "ca"], Number(f.community_area)]);
  if (f.zone.trim()) all.push(["==", ["index-of", f.zone.trim().toUpperCase(), ["coalesce", ["get", "zone"], ""]], 0]);
  const sig = (s: string) => ["in", s, ["coalesce", ["get", "sig"], ""]];
  if (f.signal) all.push(sig(f.signal));
  if (f.vacant) all.push(sig("vacant_land"));
  if (f.for_sale) all.push(sig("city_owned_for_sale"));
  if (f.fast_path) all.push(["==", ["get", "fp"], true]);
  return all as FilterSpecification;
}

const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);

function salePopup(p: Record<string, unknown>): string {
  const src = p.src === "land_bank" ? "Cook County Land Bank" : "City of Chicago (ChiBlockBuilder and city land inventory)";
  const money = (v: unknown) => (typeof v === "number" ? usd(v) : null);
  const rows: [string, string | null][] = [
    ["Status", (p.status as string) ?? null],
    ["Asking price", money(p.ask)],
    ["Minimum bid", money(p.min_bid)],
    ["City land value", money(p.city_value)],
    ["Lot", typeof p.sqft === "number" ? `${num(p.sqft)} sq ft` : null],
    ["Zoning", (p.zoning as string) ?? null],
    ["Offer round", (p.round as string) ?? null],
    ["Deadline", (p.deadline as string) ?? null],
    ["Listed", (p.listed_on as string) ?? null],
  ];
  return `<div class="pop"><b>${esc(titleCase(p.address as string) || "Lot for sale")}</b>
    <div class="small muted">${esc(src)}</div>
    <table>${rows
      .filter(([, v]) => v)
      .map(([k, v]) => `<tr><td>${esc(k)}</td><td class="mono">${esc(v)}</td></tr>`)
      .join("")}</table>
    ${p.apply_url ? `<a href="${esc(p.apply_url)}" target="_blank" rel="noreferrer">Apply or see the listing</a><br>` : ""}
    ${p.pin10 ? `<a href="/parcels/${esc(p.pin10)}">Parcel page</a> · ` : ""}<span class="small muted">Source: ${esc(src)} listing, copied ${esc(p.pulled_on)}</span></div>`;
}

function landPopup(p: Record<string, unknown>): string {
  const kind = p.kind === "nbhd" ? "Assessor neighborhood" : "Community area";
  const thin = typeof p.sales === "number" && p.sales < 5;
  return `<div class="pop"><b>${esc(kind)} ${esc(p.kind === "nbhd" ? p.code : titleCase(p.name as string))}</b>
    ${p.kind === "nbhd" ? `<div class="small muted">${esc(p.name)} township</div>` : ""}
    <table>
      <tr><td>Median land sale</td><td class="mono">${esc(usd(p.per_sqft as number))} per lot sq ft</td></tr>
      <tr><td>Sales</td><td class="mono">${esc(p.sales)}${thin ? " (thin: fewer than 5)" : ""}</td></tr>
      ${p.vacant_per_sqft ? `<tr><td>Vacant lots only</td><td class="mono">${esc(usd(p.vacant_per_sqft as number))} (${esc(p.vacant_sales)} sales)</td></tr>` : ""}
      <tr><td>Sale dates</td><td class="mono">${esc(p.first_sale)} to ${esc(p.last_sale)}</td></tr>
    </table>
    <span class="small muted">Source: Cook County Assessor sales of vacant lots and teardowns, last 36 months; computed ${esc(p.computed_on)}</span></div>`;
}

function readFilters(sp: URLSearchParams): Filters {
  const f = { ...DEFAULT_FILTERS };
  for (const k of Object.keys(f) as (keyof Filters)[]) {
    const v = sp.get(k);
    if (v === null) continue;
    if (typeof f[k] === "boolean") (f as Record<string, unknown>)[k] = v === "true";
    else (f as Record<string, unknown>)[k] = v;
  }
  return f;
}

export function MapScreen({ areas, initial }: { areas: CommunityArea[]; initial: Record<string, string> }) {
  const [filters, setFilters] = useState<Filters>(() => readFilters(new URLSearchParams(initial)));
  const [lots, setLots] = useState<Lot[]>([]);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Lot | null>(null);
  const [snapshot, setSnapshot] = useState<AreaSnapshot | null>(null);
  const [layers, setLayers] = useState({ fast: false, land: false, landKind: "nbhd", sale: false });
  const [basemap, setBasemap] = useState<"loading" | "ok" | "plain">("loading");
  const [timing, setTiming] = useState<{ list?: number; map?: number }>({});
  const [zoom, setZoom] = useState(11);
  const mapRef = useRef<MLMap | null>(null);
  const mapDiv = useRef<HTMLDivElement>(null);
  const markers = useRef<Marker[]>([]);
  const lib = useRef<typeof import("maplibre-gl") | null>(null);
  const seq = useRef(0);
  const t0 = useRef(0);
  const [ready, setReady] = useState(false);

  const areaName = useMemo(() => areas.find((a) => String(a.num) === filters.community_area)?.name, [areas, filters.community_area]);

  // Load the list whenever the filters change.
  const load = useCallback(async (f: Filters, offset: number) => {
    const my = ++seq.current;
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const res = await fetch(`/api/lots?${lotsQuery(f, offset)}`);
      const body = (await res.json()) as Lot[] | { detail: string };
      if (my !== seq.current) return;
      if (!res.ok || !Array.isArray(body)) throw new Error(!Array.isArray(body) ? body.detail : res.statusText);
      setLots((prev) => (offset ? [...prev, ...body] : body));
      setMore(body.length === PAGE);
      setTiming((t) => ({ ...t, list: Math.round(performance.now() - start) }));
    } catch (e) {
      if (my === seq.current) setError(`Could not load the list: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      if (my === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    t0.current = performance.now();
    void load(filters, 0);
    const u = new URL(window.location.href);
    u.search = lotsQuery(filters, 0).replace(/&?limit=\d+|&?offset=\d+/g, "");
    window.history.replaceState(null, "", u);
  }, [filters, load]);

  // Area snapshot.
  useEffect(() => {
    setSnapshot(null);
    if (!filters.community_area) return;
    let live = true;
    fetch(`/api/community-areas/${filters.community_area}/snapshot`)
      .then((r) => (r.ok ? r.json() : null))
      .then((s: AreaSnapshot | null) => live && setSnapshot(s))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [filters.community_area]);

  const selectPin = useCallback(async (pin10: string) => {
    const res = await fetch(`/api/lots/${pin10}`);
    if (res.ok) setSelected((await res.json()) as Lot);
  }, []);

  // Build the map once.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const maplibregl = await import("maplibre-gl");
      lib.current = maplibregl;
      let style: StyleSpecification = {
        version: 8,
        sources: {},
        layers: [{ id: "bg", type: "background", paint: { "background-color": "#eceeea" } }],
      };
      let ok = false;
      if (BASEMAP !== "none") {
        try {
          const r = await fetch(BASEMAP, { signal: AbortSignal.timeout(5000) });
          if (r.ok) {
            style = (await r.json()) as StyleSpecification;
            ok = true;
          }
        } catch {
          // no basemap: lots on a plain background
        }
      }
      if (cancelled || !mapDiv.current) return;
      setBasemap(ok ? "ok" : "plain");
      const map = new maplibregl.Map({
        container: mapDiv.current,
        style,
        bounds: CHICAGO,
        minZoom: 9,
        maxZoom: 19,
        attributionControl: { compact: false },
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
      map.on("load", () => {
        const origin = window.location.origin;
        const attribution = "Parcels: Cook County Assessor; zoning and city land: City of Chicago; score: 25x125 nightly";
        map.addSource("lots", { type: "vector", tiles: [`${origin}/tiles/lots/{z}/{x}/{y}`], minzoom: 10, maxzoom: 16, attribution });
        map.addSource("land_value", { type: "vector", tiles: [`${origin}/tiles/land_value/{z}/{x}/{y}`], minzoom: 9, maxzoom: 14 });
        map.addSource("lots_for_sale", { type: "vector", tiles: [`${origin}/tiles/lots_for_sale/{z}/{x}/{y}`], minzoom: 9, maxzoom: 16 });
        // Put our layers under the basemap's labels when there are any.
        const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
        map.addLayer({ id: "land-fill", type: "fill", source: "land_value", "source-layer": "land_value",
          layout: { visibility: "none" }, filter: ["==", ["get", "kind"], "nbhd"],
          paint: { "fill-color": stepExpr("per_sqft", LAND_STEPS), "fill-opacity": ["case", ["<", ["get", "sales"], 5], 0.25, 0.55] } }, firstLabel); // prettier-ignore
        map.addLayer({ id: "land-line", type: "line", source: "land_value", "source-layer": "land_value",
          layout: { visibility: "none" }, filter: ["==", ["get", "kind"], "nbhd"],
          paint: { "line-color": "#8a4600", "line-width": 1, "line-opacity": 0.6 } }, firstLabel); // prettier-ignore
        map.addLayer({ id: "lots-fill", type: "fill", source: "lots", "source-layer": "lots", minzoom: 14,
          filter: ["==", ["geometry-type"], "Polygon"],
          paint: { "fill-color": stepExpr("score", SCORE_STEPS), "fill-opacity": 0.8 } }, firstLabel); // prettier-ignore
        map.addLayer({ id: "lots-line", type: "line", source: "lots", "source-layer": "lots", minzoom: 15,
          paint: { "line-color": "#ffffff", "line-width": 0.6 } }, firstLabel); // prettier-ignore
        map.addLayer({ id: "lots-pt", type: "circle", source: "lots", "source-layer": "lots", maxzoom: 14,
          filter: ["==", ["geometry-type"], "Point"],
          paint: { "circle-color": stepExpr("score", SCORE_STEPS), "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 1.6, 13, 3.5],
                   "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10, 0, 13, 0.6] } }); // prettier-ignore
        map.addLayer({ id: "fast-line", type: "line", source: "lots", "source-layer": "lots", minzoom: 14,
          layout: { visibility: "none" }, filter: ["==", ["get", "fp"], true],
          paint: { "line-color": "#1d7a52", "line-width": 2.5 } }); // prettier-ignore
        map.addLayer({ id: "fast-pt", type: "circle", source: "lots", "source-layer": "lots", maxzoom: 14,
          layout: { visibility: "none" }, filter: ["==", ["get", "fp"], true],
          paint: { "circle-color": "rgba(0,0,0,0)", "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 3, 13, 5.5],
                   "circle-stroke-color": "#1d7a52", "circle-stroke-width": 1.5 } }); // prettier-ignore
        map.addLayer({ id: "sel-line", type: "line", source: "lots", "source-layer": "lots",
          filter: ["==", ["get", "pin10"], ""], paint: { "line-color": "#d4380d", "line-width": 3 } }); // prettier-ignore
        map.addLayer({ id: "sale-pt", type: "circle", source: "lots_for_sale", "source-layer": "lots_for_sale",
          layout: { visibility: "none" },
          paint: { "circle-color": ["match", ["get", "src"], "land_bank", SALE_COLORS.land_bank, SALE_COLORS.city],
                   "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 2.5, 15, 7], "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 } }); // prettier-ignore

        map.on("click", (e) => {
          const hits = map.queryRenderedFeatures(e.point, { layers: ["sale-pt", "lots-fill", "lots-pt", "land-fill"].filter((id) => map.getLayoutProperty(id, "visibility") !== "none") });
          const sale = hits.find((h) => h.layer.id === "sale-pt");
          const lot = hits.find((h) => h.layer.id === "lots-fill" || h.layer.id === "lots-pt");
          const land = hits.find((h) => h.layer.id === "land-fill");
          if (sale) new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(e.lngLat).setHTML(salePopup(sale.properties)).addTo(map);
          else if (lot) void selectPin(String(lot.properties.pin10));
          else if (land) new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(e.lngLat).setHTML(landPopup(land.properties)).addTo(map);
        });
        for (const id of ["sale-pt", "lots-fill", "lots-pt"]) {
          map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
        }
        map.on("zoomend", () => setZoom(map.getZoom()));
        // For the smoke test's timing: when the map last finished drawing.
        map.on("idle", () => (document.body.dataset.mapIdle = String(Date.now())));
        setZoom(map.getZoom());
        setReady(true);
      });
    })();
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [selectPin]);

  // Filters on the map layers, and the map's time to settle after a change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const f = mapFilter(filters);
    map.setFilter("lots-fill", ["all", ["==", ["geometry-type"], "Polygon"], f] as FilterSpecification);
    map.setFilter("lots-pt", ["all", ["==", ["geometry-type"], "Point"], f] as FilterSpecification);
    map.setFilter("fast-line", ["all", ["==", ["get", "fp"], true], f] as FilterSpecification);
    map.setFilter("fast-pt", ["all", ["==", ["geometry-type"], "Point"], ["==", ["get", "fp"], true], f] as FilterSpecification);
    const start = t0.current || performance.now();
    map.once("idle", () => setTiming((t) => ({ ...t, map: Math.round(performance.now() - start) })));
    map.triggerRepaint();
  }, [filters, ready]);

  // Fit to the chosen area.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const a = areas.find((x) => String(x.num) === filters.community_area);
    map.fitBounds(a ? a.bounds : CHICAGO, { padding: 30, duration: 0 });
  }, [filters.community_area, areas, ready]);

  // Layer toggles.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const vis = (on: boolean) => (on ? "visible" : "none");
    map.setLayoutProperty("fast-line", "visibility", vis(layers.fast));
    map.setLayoutProperty("fast-pt", "visibility", vis(layers.fast));
    map.setLayoutProperty("land-fill", "visibility", vis(layers.land));
    map.setLayoutProperty("land-line", "visibility", vis(layers.land));
    map.setFilter("land-fill", ["==", ["get", "kind"], layers.landKind]);
    map.setFilter("land-line", ["==", ["get", "kind"], layers.landKind]);
    map.setLayoutProperty("sale-pt", "visibility", vis(layers.sale));
  }, [layers, ready]);

  // Numbered pins for the lots in the list.
  useEffect(() => {
    const map = mapRef.current;
    const ml = lib.current;
    if (!map || !ml || !ready) return;
    for (const m of markers.current) m.remove();
    markers.current = lots
      .map((l, i) => {
        if (l.lat === null || l.lon === null) return null;
        const el = document.createElement("button");
        el.type = "button";
        el.className = `pin${selected?.pin10 === l.pin10 ? " on" : ""}`;
        el.textContent = String(i + 1);
        el.setAttribute("aria-label", `${i + 1}: ${titleCase(l.address) || l.pin10}, score ${num(l.score)}`);
        el.addEventListener("click", (ev) => {
          ev.stopPropagation();
          setSelected(l);
        });
        return new ml.Marker({ element: el }).setLngLat([l.lon, l.lat]).addTo(map);
      })
      .filter((m): m is Marker => m !== null);
  }, [lots, ready, selected?.pin10]);

  // Highlight and show the selected lot.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setFilter("sel-line", ["==", ["get", "pin10"], selected?.pin10 ?? ""]);
  }, [selected, ready]);

  const pick = (l: Lot) => {
    setSelected(l);
    const map = mapRef.current;
    if (map && l.lon !== null && l.lat !== null) map.easeTo({ center: [l.lon, l.lat], zoom: Math.max(map.getZoom(), 16), duration: 600 });
  };

  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => setFilters((f) => ({ ...f, [k]: v }));
  const chips: { key: "vacant" | "for_sale" | "fast_path"; label: string }[] = [
    { key: "vacant", label: "Vacant land" },
    { key: "for_sale", label: "City-owned lot for sale" },
    { key: "fast_path", label: "Fast path (by right, no zoning relief)" },
  ];
  const computedOn = lots[0]?.computed_on;
  const floor = zoom >= 14 ? null : zoom >= 13 ? 20 : zoom >= 11 ? 40 : 50;

  return (
    <div className="mapscreen">
      <section aria-label="Search and filters" className="filters">
        <div className="frow">
          <label className="fl grow">
            Area
            <select value={filters.community_area} onChange={(e) => set("community_area", e.target.value)} data-testid="area">
              <option value="">All of Chicago</option>
              {areas.map((a) => (
                <option key={a.num} value={a.num}>
                  {a.name} (community area {a.num})
                </option>
              ))}
            </select>
          </label>
          <label className="fl">
            Zoning starts with
            <input value={filters.zone} placeholder="RT-4, B2, RS" onChange={(e) => set("zone", e.target.value)} data-testid="zone" />
          </label>
          <label className="fl small-w">
            Min. score
            <input type="number" min={0} max={100} value={filters.min_score} onChange={(e) => set("min_score", e.target.value)} data-testid="min-score" />
          </label>
          <label className="fl small-w">
            Min. units by right
            <input type="number" min={0} max={20} value={filters.min_units} onChange={(e) => set("min_units", e.target.value)} />
          </label>
          <label className="fl">
            Other signal
            <select value={filters.signal} onChange={(e) => set("signal", e.target.value)}>
              <option value="">Any</option>
              {SIGNAL_CHOICES.map((s) => (
                <option key={s} value={s}>
                  {SIGNAL_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
          <a className="btn small" href={`/api/lots?${lotsQuery(filters, 0, "csv")}`} data-testid="csv">
            Export list as CSV
          </a>
          <SaveSearch params={lotsQuery(filters, 0).replace(/&?(limit|offset)=\d+/g, "").replace(/^&/, "")} suggested={areaName ? `${areaName} lots` : "Saved search"} />
          <button className="btn small" type="button" onClick={() => setFilters(DEFAULT_FILTERS)}>
            Clear
          </button>
        </div>
        <div role="group" aria-label="Signals" className="chips">
          {chips.map((c) => (
            <button key={c.key} type="button" className="chip" aria-pressed={filters[c.key]} onClick={() => set(c.key, !filters[c.key])}>
              {c.label}
            </button>
          ))}
        </div>
      </section>

      {snapshot && (
        <section aria-label="Area snapshot" className="snapshot">
          <span>
            <strong>{snapshot.name}</strong> · new 2-6 unit buildings and condos
          </span>
          {snapshot.sales.map((s) => (
            <span key={s.kind}>
              Median new-construction {s.kind === "condo" ? "condo" : "building"} sale per unit <strong className="mono">{usd(s.median_per_unit)}</strong> ·{" "}
              <strong className="mono">{s.sales}</strong> sales {s.first_sale} to {s.last_sale}
            </span>
          ))}
          {snapshot.sales.length === 0 && <span>No new-construction sales here in the last 3 years</span>}
          {snapshot.cost_index && (
            <span>
              Cost index <strong className="mono">{snapshot.cost_index.index.toFixed(2)}</strong> ({snapshot.cost_index.permits} permits
              {snapshot.cost_index.thin ? ", blended with neighbors" : ""})
            </span>
          )}
          {snapshot.land_value && (
            <span>
              Land <strong className="mono">{usd(snapshot.land_value.per_lot_sqft)}</strong> per lot sq ft ({snapshot.land_value.sales} sales)
            </span>
          )}
          <Source>
            {snapshot.sales_source}; computed {snapshot.sales[0]?.computed_on ?? "n/a"}.{" "}
            {snapshot.cost_index && `${snapshot.cost_index.source}; computed ${snapshot.cost_index.computed_on}. `}
            {snapshot.land_value && `${snapshot.land_value.source}; computed ${snapshot.land_value.computed_on}.`}
          </Source>
        </section>
      )}

      <main className="mapgrid">
        <section aria-label="Results" className="results">
          <div className="rhead">
            <span>
              <b data-testid="count">{loading && lots.length === 0 ? "Loading" : `${lots.length}${more ? "+" : ""} lots`}</b>
              <span className="small muted"> {areaName ? `in ${areaName}` : "in Chicago"}</span>
            </span>
            <label className="small muted sortl">
              Sort
              <select value={filters.sort} onChange={(e) => set("sort", e.target.value)} data-testid="sort">
                {SORTS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="small muted rnote">
            Score: {SCORE_LABEL} Nightly run of {computedOn ?? "n/a"}. Profit and max land are the by-right program at the central estimate.
            {timing.list !== undefined && ` Last update: list ${timing.list} ms`}
            {timing.map !== undefined && `, map ${timing.map} ms.`}
          </p>
          {error && <p className="err rnote">{error}</p>}
          {!loading && lots.length === 0 && !error && <p className="rnote">No lots match these filters.</p>}
          <ol className="rlist" data-testid="results">
            {lots.map((l, i) => (
              <li key={l.pin10} className={selected?.pin10 === l.pin10 ? "on" : undefined}>
                <button type="button" className="rrow" onClick={() => pick(l)}>
                  <span className="rnum">{i + 1}</span>
                  <span className="rbody">
                    <span className="rtop">
                      <span className="raddr">{titleCase(l.address) || `Lot ${l.pin10}`}</span>
                      <span className="rscore mono">{num(l.score)}</span>
                    </span>
                    <span className="small muted">
                      {l.zone_class ?? "n/a"} · {l.lot_sqft ? `${num(l.lot_sqft)} sq ft` : "lot size n/a"} · {l.by_right_units ?? 0} units by right
                      {l.units_now ? `, ${l.units_now} standing` : ""} · {titleCase(l.community_area)}
                    </span>
                    <span className="rtags">
                      {l.details.fast_path && <span className="tag g">Fast path</span>}
                      {(l.details.signals ?? []).map((s) => (
                        <span key={s} className="tag n">
                          {SIGNAL_LABELS[s] ?? s}
                        </span>
                      ))}
                      {(l.details.penalties ?? []).map((s) => (
                        <span key={s} className="tag c">
                          {PENALTY_LABELS[s] ?? s}
                        </span>
                      ))}
                    </span>
                    <span className="rpts mono small">
                      Zoning {num(l.zoning_upside)} · Profit {num(l.profit)} · Signals {num(l.acquisition)} · Location {num(l.location)} · Incentives{" "}
                      {num(l.incentives)} · Penalties {num(l.penalties)}
                    </span>
                    <span className="small">
                      {l.profit_central !== null ? (
                        <>
                          Est. profit <b className="mono">{usdK(l.profit_central)}</b> · return on cost {pct(l.return_on_cost)} · Max land{" "}
                          <b className="mono">{usdK(l.max_land_price)}</b>
                        </>
                      ) : (
                        <span className="muted">No profit points: {l.details.profit ?? "not priced"}</span>
                      )}
                      {l.profit_central !== null && l.details.profit && <span className="muted"> · No profit points: {l.details.profit}</span>}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
          {more && (
            <div className="rnote">
              <button className="btn small" type="button" disabled={loading} onClick={() => void load(filters, lots.length)}>
                Show {PAGE} more
              </button>
            </div>
          )}
        </section>

        <section aria-label="Map" className="mapbox">
          <div ref={mapDiv} className="mapcanvas" data-testid="map" />
          {selected && <LotPanel lot={selected} onClose={() => setSelected(null)} />}
          <div className="legend">
            <b>Development score</b>
            <span className="ramp">
              {SCORE_STEPS.map((s, i) => (
                <span key={s.from}>
                  <i style={{ background: s.color }} />
                  {s.from}
                  {i < SCORE_STEPS.length - 1 ? `-${SCORE_STEPS[i + 1].from - 1}` : "+"}
                </span>
              ))}
            </span>
            {floor !== null && <span className="small muted">Zoomed out: lots scoring {floor}+ only. Zoom in for every lot.</span>}
            <b style={{ marginTop: 6 }}>Map layers</b>
            <label>
              <input type="checkbox" checked={layers.fast} onChange={(e) => setLayers((l) => ({ ...l, fast: e.target.checked }))} data-testid="layer-fast" /> Fast-path lots{" "}
              <i className="sw" style={{ border: "2px solid #1d7a52" }} />
            </label>
            <label>
              <input type="checkbox" checked={layers.land} onChange={(e) => setLayers((l) => ({ ...l, land: e.target.checked }))} data-testid="layer-land" /> Land value per lot sq ft
            </label>
            {layers.land && (
              <>
                <select value={layers.landKind} onChange={(e) => setLayers((l) => ({ ...l, landKind: e.target.value }))} className="mini">
                  <option value="nbhd">by Assessor neighborhood</option>
                  <option value="community_area">by community area</option>
                </select>
                <span className="ramp">
                  {LAND_STEPS.map((s, i) => (
                    <span key={s.from}>
                      <i style={{ background: s.color }} />${s.from}
                      {i < LAND_STEPS.length - 1 ? `-${LAND_STEPS[i + 1].from}` : "+"}
                    </span>
                  ))}
                </span>
                <span className="small muted">Paler where fewer than 5 sales. Click an area for its sales and dates.</span>
              </>
            )}
            <label>
              <input type="checkbox" checked={layers.sale} onChange={(e) => setLayers((l) => ({ ...l, sale: e.target.checked }))} data-testid="layer-sale" /> Public lots for sale
            </label>
            {layers.sale && (
              <span className="small">
                <i className="sw dot" style={{ background: SALE_COLORS.city }} /> City (ChiBlockBuilder){" "}
                <i className="sw dot" style={{ background: SALE_COLORS.land_bank }} /> Cook County Land Bank
              </span>
            )}
            {basemap === "plain" && <span className="small muted">Basemap could not load; lots show on a plain background.</span>}
          </div>
        </section>
      </main>
      <p className="small muted" style={{ padding: "8px 24px" }}>
        Every lot shows the points behind its score. <Link href="/">Search by address or PIN</Link>.
      </p>
    </div>
  );
}
