// A note on every screen when a nightly source is over 36 hours old (engine /health, data/rules/freshness.json).
import { ENGINE_URL } from "../lib/claim";
import type { Freshness } from "../lib/types";

const fmt = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "America/Chicago" });

export async function StaleDataNote() {
  let f: Freshness;
  try {
    const res = await fetch(`${ENGINE_URL}/health`, { next: { revalidate: 300 } });
    f = (await res.json()) as Freshness;
  } catch {
    return null;
  }
  if (f.status !== "stale" || !f.stale?.length) return null;
  const list = f.stale
    .slice(0, 4)
    .map((s) => `${s.label} (last copied ${fmt(s.finished_at)})`)
    .join(", ");
  const more = f.stale.length > 4 ? ` and ${f.stale.length - 4} more` : "";
  return (
    <div className="warnline" role="note" data-testid="stale-note" style={{ padding: "8px 24px", fontSize: 13 }}>
      Some nightly data is more than {f.stale_after_hours ?? 36} hours old: {list}
      {more}. Numbers that use it are as of those dates.
    </div>
  );
}
