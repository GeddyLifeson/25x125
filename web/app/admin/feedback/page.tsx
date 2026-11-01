import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { getFeedback, getFeedbackSummary, settle } from "../../../lib/engine";
import type { Comparison, FeedbackRow, FeedbackSummary, Spread } from "../../../lib/feedback";
import { formatPin, num, usd } from "../../../lib/format";
import { getSession } from "../../../lib/session";

export const dynamic = "force-dynamic";
export const metadata = { title: "Feedback received · 25x125" };

const ratio = (r: Spread) => (r ? `${r.median.toFixed(2)}x (${r.low.toFixed(2)}x to ${r.high.toFixed(2)}x)` : "n/a");

function dollars(d: Spread, perSqft: boolean): string {
  if (!d) return "n/a";
  const f = (n: number) => (perSqft ? `${n < 0 ? "-" : "+"}$${Math.abs(n).toFixed(2)}` : `${n < 0 ? "-" : "+"}${usd(Math.abs(n))}`);
  return `${f(d.median)} (${f(d.low)} to ${f(d.high)})`;
}

function Cmp({ c, perSqft }: { c?: Comparison; perSqft?: boolean }) {
  if (!c) return <span className="muted">n/a</span>;
  const f = (n: number) => (perSqft ? `$${n.toFixed(2)}` : usd(n));
  return (
    <>
      {f(c.own)} vs {f(c.app)}
      <div className="basis">
        {c.difference < 0 ? "-" : "+"}
        {f(Math.abs(c.difference))} · {c.ratio.toFixed(2)}x
      </div>
    </>
  );
}

function Stats({ s }: { s: FeedbackSummary }) {
  const rows: [keyof FeedbackSummary["comparisons"], string, boolean][] = [
    ["cost_per_sqft", "Hard cost per sq ft", true],
    ["cost_total", "Total cost", false],
    ["sale_per_unit", "Sale price per unit", false],
  ];
  return (
    <section className="card" data-testid="feedback-summary">
      <h2>Summary</h2>
      <p className="sub small">{s.note} Median, then the lowest and highest entry.</p>
      <div className="fbstats">
        <div>
          <span className="k">Entries</span>
          <span className="v" data-testid="feedback-count">
            {s.count}
          </span>
        </div>
        <div>
          <span className="k">Median rating (1 far off, 5 about right)</span>
          <span className="v">{s.rating.median ?? "n/a"}</span>
          <span className="small muted">from {s.rating.n} ratings</span>
        </div>
        <div>
          <span className="k">Would use it</span>
          <span className="v">
            {s.would_use.yes} yes · {s.would_use.maybe} maybe · {s.would_use.no} no
          </span>
        </div>
        <div>
          <span className="k">Time spent</span>
          <span className="v">{num(s.minutes_spent.total)} min</span>
          <span className="small muted">over {s.minutes_spent.n} entries</span>
        </div>
      </div>
      <div className="scroll" style={{ marginTop: 14 }}>
        <table className="t">
          <thead>
            <tr>
              <th>Their figure vs the app's</th>
              <th className="num">Entries</th>
              <th className="num">Ratio</th>
              <th className="num">Difference in dollars</th>
              <th className="num">Median theirs / app</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, label, sq]) => {
              const c = s.comparisons[k];
              const f = (n: number | null) => (n === null ? "n/a" : sq ? `$${n.toFixed(2)}` : usd(n));
              return (
                <tr key={k}>
                  <td>{label}</td>
                  <td className="num">{c.n}</td>
                  <td className="num">{ratio(c.ratio)}</td>
                  <td className="num">{dollars(c.difference, sq)}</td>
                  <td className="num">
                    {f(c.own_median)} / {f(c.app_median)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Entries({ rows }: { rows: FeedbackRow[] }) {
  return (
    <section className="card">
      <h2>Entries</h2>
      <p className="sub small">Newest first. The app's figures are the ones on screen when the form was opened.</p>
      <div className="scroll">
        <table className="t" data-testid="feedback-table">
          <thead>
            <tr>
              <th>When and who</th>
              <th>Lot</th>
              <th className="num">Rating</th>
              <th className="num">Hard cost per sq ft</th>
              <th className="num">Total cost</th>
              <th className="num">Sale per unit</th>
              <th>Wrong</th>
              <th>Looked up elsewhere</th>
              <th>Missing</th>
              <th>Use it</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  {r.created_at.slice(0, 16).replace("T", " ")}
                  <div className="basis">
                    #{r.id} · {r.email ?? "account deleted"}
                    {r.minutes_spent !== null ? ` · ${r.minutes_spent} min` : ""}
                  </div>
                </td>
                <td>
                  {r.pin ? (
                    <Link href={`/parcels/${r.pin}/feasibility`}>{r.app_snapshot.address ?? formatPin(r.pin)}</Link>
                  ) : (
                    <span className="muted">general</span>
                  )}
                  <div className="basis">
                    {r.scenario ? `scenario ${r.scenario}` : r.page_path ?? ""}
                    {r.app_snapshot.preset ? ` · ${r.app_snapshot.preset}` : ""}
                    {r.app_snapshot.cost_index !== undefined ? ` · index ${num(r.app_snapshot.cost_index, 2)}` : ""}
                  </div>
                </td>
                <td className="num">{r.rating ?? "n/a"}</td>
                <td className="num">
                  <Cmp c={r.comparisons.cost_per_sqft} perSqft />
                </td>
                <td className="num">
                  <Cmp c={r.comparisons.cost_total} />
                </td>
                <td className="num">
                  <Cmp c={r.comparisons.sale_per_unit} />
                </td>
                <td className="fbtext small">{r.numbers_wrong}</td>
                <td className="fbtext small">{r.outside_questions}</td>
                <td className="fbtext small">{r.missing}</td>
                <td>{r.would_use ?? ""}</td>
                <td className="fbtext small">{r.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default async function AdminFeedbackPage() {
  const session = await getSession();
  if (!session) redirect("/signin?next=/admin/feedback");
  if (!session.is_admin) notFound();
  const [rows, summary] = await Promise.all([settle(getFeedback(500)), settle(getFeedbackSummary())]);
  if (!rows.ok && (rows.status === 403 || rows.status === 401)) notFound();
  return (
    <main className="wrap">
      <section className="head">
        <div>
          <h1>Feedback received</h1>
          <span className="muted">What people checking the numbers sent. Only product admins see this page.</span>
        </div>
        <div className="btns">
          <a className="btn small" href="/api/feedback/csv" data-testid="feedback-csv">
            Download all as CSV
          </a>
        </div>
      </section>
      {!rows.ok || !summary.ok ? (
        <p className="err">Could not load feedback: {!rows.ok ? rows.error : !summary.ok ? summary.error : ""}</p>
      ) : (
        <>
          <Stats s={summary.value} />
          {rows.value.length === 0 ? <p className="muted">No entries yet.</p> : <Entries rows={rows.value} />}
        </>
      )}
    </main>
  );
}
