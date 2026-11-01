"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Source } from "../../components/Source";
import { num, titleCase, usd, usdK } from "../../lib/format";
import { EVENT_KINDS, OUTREACH_NOTE, STAGES } from "../../lib/labels";
import type { Deal, DealEvent } from "../../lib/types";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/deals${path}`, init);
  if (res.status === 204) return undefined as T;
  const body = (await res.json()) as T | { detail?: unknown };
  if (!res.ok) {
    const d = (body as { detail?: unknown }).detail;
    throw new Error(typeof d === "string" ? d : JSON.stringify(d ?? res.statusText));
  }
  return body as T;
}

const jsonInit = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

/** Profit and max land with where they came from: the saved feasibility run, or the nightly score. */
function headline(d: Deal): { profit: string; maxLand: string; src: string; hold: boolean } {
  const r = d.result;
  if (r) {
    const hold = r.exit === "hold";
    return {
      profit: hold ? `NOI ${usdK(r.noi)}/yr` : usdK(r.profit),
      maxLand: hold ? "n/a" : usdK(r.max_land_price),
      src: `${r.source}, ${r.run_on}. ${r.name}, ${r.units} units, ${r.exit === "hold" ? "build and hold" : "build and sell"}. Total cost ${usd(r.total_cost)} (-${usd(r.total_cost - r.total_cost_low)} / +${usd(r.total_cost_high - r.total_cost)})${r.profit_p10 != null && r.profit_p90 != null ? `; profit 10th-90th percentile ${usd(r.profit_p10)} to ${usd(r.profit_p90)}` : ""}.`,
      hold,
    };
  }
  const n = d.nightly;
  if (n) {
    return {
      profit: usdK(n.profit_central),
      maxLand: usdK(n.max_land_price),
      src: `${n.source}, ${n.computed_on}: ${n.by_right_units ?? 0} units by right at the central estimate. Run feasibility and save to replace it.`,
      hold: false,
    };
  }
  return { profit: "n/a", maxLand: "n/a", src: "No numbers yet: run feasibility and save.", hold: false };
}

function pdfHref(d: Deal): string {
  const qs = new URLSearchParams({ exit: d.exit ?? "sell", s: String(d.scenario ?? 0) });
  if (d.target) qs.set("target", d.target);
  if (d.overrides && Object.keys(d.overrides).length) qs.set("o", JSON.stringify(d.overrides));
  return `/parcels/${d.pin}/report.pdf?${qs}`;
}

export function DealsScreen({ initial, initialPick }: { initial: Deal[]; initialPick: number | null }) {
  const [deals, setDeals] = useState<Deal[]>(initial);
  const [filter, setFilter] = useState<string>("all");
  const [pick, setPick] = useState<number | null>(initialPick ?? initial[0]?.id ?? null);
  const [events, setEvents] = useState<DealEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({ kind: "call", event_on: new Date().toISOString().slice(0, 10), note: "" });
  const fileRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    try {
      setDeals(await api<Deal[]>(""));
    } catch (e) {
      setError(`Could not load deals: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, []);

  const picked = deals.find((d) => d.id === pick) ?? null;

  useEffect(() => {
    if (pick === null) {
      setEvents([]);
      return;
    }
    let live = true;
    api<DealEvent[]>(`/${pick}/events`)
      .then((ev) => live && setEvents(ev))
      .catch(() => live && setEvents([]));
    return () => {
      live = false;
    };
  }, [pick]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: deals.length };
    for (const s of STAGES) c[s.id] = deals.filter((d) => d.stage === s.id).length;
    return c;
  }, [deals]);
  const rows = deals.filter((d) => filter === "all" || d.stage === filter);

  const patch = async (id: number, body: Record<string, unknown>) => {
    setError(null);
    try {
      const d = await api<Deal>(`/${id}`, jsonInit("PATCH", body));
      setDeals((prev) => prev.map((x) => (x.id === id ? d : x)));
    } catch (e) {
      setError(`Could not save: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const remove = async (d: Deal) => {
    if (!window.confirm(`Delete the deal for ${titleCase(d.address) || d.pin} and its outreach log?`)) return;
    await api(`/${d.id}`, { method: "DELETE" });
    if (pick === d.id) setPick(null);
    await reload();
  };

  const logContact = async () => {
    if (pick === null) return;
    setError(null);
    try {
      await api<DealEvent>(`/${pick}/events`, jsonInit("POST", form));
      setEvents(await api<DealEvent[]>(`/${pick}/events`));
      setForm((f) => ({ ...f, note: "" }));
    } catch (e) {
      setError(`Could not log: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const removeEvent = async (id: number) => {
    if (pick === null) return;
    await api(`/${pick}/events/${id}`, { method: "DELETE" });
    setEvents(await api<DealEvent[]>(`/${pick}/events`));
  };

  const importCsv = async (file: File) => {
    setError(null);
    setNotice(null);
    try {
      const r = await api<{ created: number; updated: number; errors: string[] }>("/import", {
        method: "POST",
        headers: { "content-type": "text/csv" },
        body: await file.text(),
      });
      setNotice(`Imported ${file.name}: ${r.created} new, ${r.updated} updated.`);
      if (r.errors.length) setError(`Skipped: ${r.errors.slice(0, 5).join("; ")}${r.errors.length > 5 ? ` (+${r.errors.length - 5} more)` : ""}`);
      await reload();
    } catch (e) {
      setError(`Import failed: ${e instanceof Error ? e.message : String(e)}`);
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <main className="wrap">
      <section className="head">
        <div>
          <h1>Deals</h1>
          <span className="muted">Saved parcels, their status, and every owner contact</span>
        </div>
        <div className="btns">
          <button className="btn" type="button" onClick={() => fileRef.current?.click()}>
            Import CSV
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            data-testid="deal-import"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void importCsv(f);
            }}
          />
          <a className="btn" href="/api/deals?format=csv" data-testid="deal-csv">
            Export deals CSV
          </a>
          <a className="btn" href="/api/deals/events?format=csv">
            Export outreach log CSV
          </a>
        </div>
      </section>
      {(notice || error) && (
        <div className="bar">
          {notice && <span className="status" role="status">{notice}</span>}
          {error && <span className="err">{error}</span>}
        </div>
      )}

      <section aria-label="Pipeline counts" className="stages">
        {[{ id: "all", label: "All" }, ...STAGES].map((s) => (
          <button key={s.id} type="button" className="stage" aria-pressed={filter === s.id} onClick={() => setFilter(s.id)} data-testid={`stage-${s.id}`}>
            <span className="l">{s.label}</span>
            <span className="v">{counts[s.id] ?? 0}</span>
          </button>
        ))}
      </section>

      <div className="cols">
        <section aria-label="Deal table" className="card main" style={{ padding: 0, overflowX: "auto" }}>
          {deals.length === 0 ? (
            <p style={{ padding: 20 }}>
              No deals yet. Save one from the <Link href="/map">map</Link>, a parcel page or the feasibility screen, or import a CSV with a{" "}
              <span className="mono">pin</span> column.
            </p>
          ) : (
            <table className="t deals" data-testid="deal-table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 16 }}>Parcel</th>
                  <th>Status</th>
                  <th>Best scenario</th>
                  <th className="num">Profit</th>
                  <th className="num">Max land</th>
                  <th>Next step</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => {
                  const h = headline(d);
                  return (
                    <tr key={d.id} className={pick === d.id ? "sel" : undefined} onClick={() => setPick(d.id)}>
                      <td style={{ paddingLeft: 16, minWidth: 190 }}>
                        <Link href={`/parcels/${d.pin}`} style={{ fontWeight: 500 }}>
                          {titleCase(d.address) || d.pin}
                        </Link>
                        <br />
                        <span className="small muted">
                          {d.zone_class ?? "n/a"} · {d.lot_sqft ? `${num(d.lot_sqft)} sq ft` : "lot n/a"} · {titleCase(d.community_area)}
                        </span>
                        <br />
                        <span className="small" onClick={(e) => e.stopPropagation()}>
                          <Link href={`/parcels/${d.pin}/feasibility?deal=${d.id}`}>Feasibility</Link> ·{" "}
                          <a href={pdfHref(d)} target="_blank" rel="noreferrer">
                            PDF
                          </a>{" "}
                          ·{" "}
                          <button type="button" className="linkish" onClick={() => void remove(d)}>
                            Delete
                          </button>
                        </span>
                      </td>
                      <td>
                        <select
                          aria-label="Change status"
                          className={`badge ${d.stage}`}
                          value={d.stage}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => void patch(d.id, { stage: e.target.value })}
                        >
                          {STAGES.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        {d.scenario_name ?? (d.nightly ? `By right, ${d.nightly.by_right_units ?? 0} units (nightly)` : "Not run")}
                        {d.exit && <span className="small muted"> · {d.exit === "hold" ? "hold" : "sell"}</span>}
                      </td>
                      <td className="num">
                        {h.profit} <Source>{h.src}</Source>
                      </td>
                      <td className="num">{h.maxLand}</td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <input
                          aria-label="Next step"
                          defaultValue={d.next_step ?? ""}
                          placeholder="Next step"
                          onBlur={(e) => e.target.value !== (d.next_step ?? "") && void patch(d.id, { next_step: e.target.value })}
                          style={{ width: 150, marginBottom: 4 }}
                        />
                        <br />
                        <input
                          aria-label="Next step date"
                          type="date"
                          defaultValue={d.next_step_on ?? ""}
                          onBlur={(e) => e.target.value !== (d.next_step_on ?? "") && void patch(d.id, { next_step_on: e.target.value || null })}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          <p className="small muted" style={{ padding: "10px 16px" }}>
            Profit and max land come from the feasibility run saved with the deal, or from the nightly score until one is saved. Estimates, not tax, legal,
            zoning or appraisal advice.
          </p>
        </section>

        <aside className="card side" aria-label="Owner outreach" style={{ gap: 14 }}>
          <h2>Owner outreach{picked ? ` · ${titleCase(picked.address) || picked.pin}` : ""}</h2>
          {!picked ? (
            <p className="muted">Pick a deal to see its contact log.</p>
          ) : (
            <>
              <ul className="log" data-testid="log">
                {events.length === 0 && <li className="muted">No contacts logged yet.</li>}
                {events.map((e) => (
                  <li key={e.id}>
                    <span className="lt">
                      <b>{e.kind_label}</b>
                      <span className="mono small muted">
                        {e.event_on}{" "}
                        <button type="button" className="linkish" aria-label="Delete entry" onClick={() => void removeEvent(e.id)}>
                          ×
                        </button>
                      </span>
                    </span>
                    <span style={{ color: "#3a4047" }}>{e.note}</span>
                  </li>
                ))}
              </ul>
              <div className="logform">
                <label>
                  Kind
                  <select value={form.kind} onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))} data-testid="log-kind">
                    {EVENT_KINDS.map((k) => (
                      <option key={k.id} value={k.id}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Date
                  <input type="date" value={form.event_on} onChange={(e) => setForm((f) => ({ ...f, event_on: e.target.value }))} />
                </label>
                <label className="full">
                  Add a note
                  <textarea rows={3} value={form.note} onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))} data-testid="log-note" />
                </label>
                <button className="btn dark full" type="button" onClick={() => void logContact()}>
                  Log contact
                </button>
              </div>
              <span className="small muted">{OUTREACH_NOTE}</span>
              <label className="small muted" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                Deal notes
                <textarea
                  key={picked.id}
                  rows={3}
                  defaultValue={picked.notes ?? ""}
                  onBlur={(e) => e.target.value !== (picked.notes ?? "") && void patch(picked.id, { notes: e.target.value })}
                  style={{ border: "1px solid #c9cfd5", borderRadius: 6, padding: 8, font: "inherit", color: "var(--ink)" }}
                />
              </label>
              <a className="small" href={`/api/deals/${picked.id}/events?format=csv`}>
                This deal&apos;s log as CSV
              </a>
            </>
          )}
        </aside>
      </div>
      <p className="small muted">
        Import file: a header row with <span className="mono">pin</span> and any of stage, next_step, next_step_on (YYYY-MM-DD), notes, address,
        overrides. A row with an existing <span className="mono">id</span> updates that deal; the export writes the same columns.
      </p>
    </main>
  );
}
