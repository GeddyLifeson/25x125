"use client";
import Link from "next/link";
import { useState } from "react";
import type { Snapshot } from "../../lib/feedback";
import { num, usd } from "../../lib/format";

type Props = {
  pin: string | null;
  scenario: "A" | "B" | "C" | null;
  pagePath: string | null;
  snapshot: Snapshot;
  signedInEmail: string | null;
};

const RATINGS: [number, string][] = [
  [1, "1 · far off"],
  [2, "2"],
  [3, "3 · somewhat close"],
  [4, "4"],
  [5, "5 · about what I would expect"],
];

const money = (raw: string): number | null => {
  const t = raw.replace(/[$,\s]/g, "");
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) && n >= 0 ? n : NaN;
};

/** "+$30 (1.17x the app)" or "-$50,000 (0.90x the app)". */
function diff(own: number | null, app: number | undefined, cents = false): string {
  if (own === null || Number.isNaN(own) || app === undefined || app <= 0) return "";
  const d = own - app;
  const amount = cents ? `$${Math.abs(d).toFixed(2)}` : usd(Math.abs(d));
  return `${d < 0 ? "-" : "+"}${amount} (${(own / app).toFixed(2)}x the app)`;
}

const perSqft = (n: number | undefined) => (n === undefined ? "n/a" : `$${n.toFixed(2)}`);

export function FeedbackForm({ pin, scenario, pagePath, snapshot: s, signedInEmail }: Props) {
  const hasNumbers = s.total_cost !== undefined;
  const [rating, setRating] = useState<number | null>(null);
  const [costSqft, setCostSqft] = useState("");
  const [costTotal, setCostTotal] = useState("");
  const [sale, setSale] = useState("");
  const [wrong, setWrong] = useState("");
  const [outside, setOutside] = useState("");
  const [missing, setMissing] = useState("");
  const [minutes, setMinutes] = useState("");
  const [wouldUse, setWouldUse] = useState<"yes" | "maybe" | "no" | null>(null);
  const [notes, setNotes] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<{ id: number } | null>(null);

  const own = { sqft: money(costSqft), total: money(costTotal), sale: money(sale) };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if ([own.sqft, own.total, own.sale].some((v) => v !== null && Number.isNaN(v))) {
      setError("Enter dollar amounts as numbers, for example 185 or 1,250,000.");
      return;
    }
    const mins = minutes.trim() === "" ? null : Number(minutes);
    if (mins !== null && (!Number.isInteger(mins) || mins < 0)) {
      setError("Enter the minutes as a whole number.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: signedInEmail ? null : email,
          page_path: pagePath,
          pin,
          scenario,
          screen: pin ? "feasibility" : "general",
          rating,
          cost_per_sqft_own: own.sqft,
          cost_total_own: own.total,
          sale_per_unit_own: own.sale,
          numbers_wrong: wrong,
          outside_questions: outside,
          missing,
          minutes_spent: mins,
          would_use: wouldUse,
          notes,
          app_snapshot: s,
        }),
      });
      const body = (await res.json().catch(() => ({}))) as { id?: number; detail?: unknown };
      if (!res.ok) {
        const d = body.detail;
        const msg = typeof d === "string" ? d : Array.isArray(d) ? "One of the answers is out of range. Check the numbers and try again." : res.statusText;
        throw new Error(msg);
      }
      setSent({ id: body.id ?? 0 });
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <section className="card" data-testid="feedback-thanks">
        <h2>Thank you</h2>
        <p>
          Your answers are saved as entry <span data-testid="feedback-id">{sent.id}</span>
          {hasNumbers ? ", next to the app's numbers you were looking at" : ""}. We read every entry.
        </p>
        <div className="bar">
          {pin && (
            <Link className="btn small primary" href={`/parcels/${pin}/feasibility`}>
              Back to feasibility
            </Link>
          )}
          <Link className="btn small" href="/map">
            Check another lot
          </Link>
        </div>
      </section>
    );
  }

  return (
    <form className="fb" onSubmit={submit} data-testid="feedback-form">
      {hasNumbers && (
        <section className="card">
          <h2>The app's numbers{scenario ? ` · scenario ${scenario}` : ""}</h2>
          <p className="sub small">
            As shown on the feasibility screen when you opened this form ({s.exit === "hold" ? "build and hold" : "build and sell"}
            {s.edits ? `, ${s.edits} edit${s.edits === 1 ? "" : "s"} applied` : ", no edits"}). These can't be changed here.
          </p>
          <dl className="fbsnap" data-testid="app-numbers">
            <div>
              <dt>Total cost</dt>
              <dd>{usd(s.total_cost)}</dd>
            </div>
            <div>
              <dt>Cost per unit</dt>
              <dd>{usd(s.cost_per_unit)}</dd>
            </div>
            <div>
              <dt>Hard cost per sq ft</dt>
              <dd>{perSqft(s.hard_cost_per_sqft)}</dd>
            </div>
            <div>
              <dt>Total cost per sq ft</dt>
              <dd>{perSqft(s.total_cost_per_sqft)}</dd>
            </div>
            <div>
              <dt>Sale price per unit</dt>
              <dd>{usd(s.sale_per_unit)}</dd>
            </div>
            <div>
              <dt>Profit</dt>
              <dd>{usd(s.profit)}</dd>
            </div>
            <div>
              <dt>Max land price at 20% return on cost</dt>
              <dd>{usd(s.max_land_price)}</dd>
            </div>
            <div>
              <dt>Build-spec preset</dt>
              <dd>{s.preset ?? "n/a"}</dd>
            </div>
            <div>
              <dt>Area cost index</dt>
              <dd>{s.cost_index !== undefined ? num(s.cost_index, 2) : "n/a"}</dd>
            </div>
            <div>
              <dt>Building</dt>
              <dd>
                {s.units ?? "n/a"} units · {num(s.gross_sqft)} sq ft
              </dd>
            </div>
          </dl>
        </section>
      )}

      <section className="card">
        <h2>Your numbers</h2>
        <p className="sub small">Leave a box empty if you don't have a figure. Dollars only.</p>
        <div className="scroll">
        <table className="t fbcmp">
          <thead>
            <tr>
              <th></th>
              {hasNumbers && <th className="num">The app</th>}
              <th>Yours</th>
              {hasNumbers && <th className="num">Difference</th>}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <label htmlFor="fb-sqft">Hard cost per sq ft for this building</label>
              </td>
              {hasNumbers && <td className="num">{perSqft(s.hard_cost_per_sqft)}</td>}
              <td>
                <input id="fb-sqft" name="cost_per_sqft_own" inputMode="decimal" placeholder="$ per sq ft" value={costSqft} onChange={(e) => setCostSqft(e.target.value)} />
              </td>
              {hasNumbers && <td className="num small">{diff(own.sqft, s.hard_cost_per_sqft, true)}</td>}
            </tr>
            <tr>
              <td>
                <label htmlFor="fb-total">Total cost, land included</label>
              </td>
              {hasNumbers && <td className="num">{usd(s.total_cost)}</td>}
              <td>
                <input id="fb-total" name="cost_total_own" inputMode="decimal" placeholder="$" value={costTotal} onChange={(e) => setCostTotal(e.target.value)} />
              </td>
              {hasNumbers && <td className="num small">{diff(own.total, s.total_cost)}</td>}
            </tr>
            <tr>
              <td>
                <label htmlFor="fb-sale">Sale price per unit</label>
              </td>
              {hasNumbers && <td className="num">{usd(s.sale_per_unit)}</td>}
              <td>
                <input id="fb-sale" name="sale_per_unit_own" inputMode="decimal" placeholder="$ per unit" value={sale} onChange={(e) => setSale(e.target.value)} />
              </td>
              {hasNumbers && <td className="num small">{diff(own.sale, s.sale_per_unit)}</td>}
            </tr>
          </tbody>
        </table>
        </div>
      </section>

      <section className="card fbq">
        <fieldset>
          <legend>How close were the numbers to what you would expect?</legend>
          <div className="fbchoices">
            {RATINGS.map(([v, label]) => (
              <label key={v}>
                <input type="radio" name="rating" value={v} checked={rating === v} onChange={() => setRating(v)} />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        <label>
          Which numbers looked wrong, and what should they be?
          <textarea name="numbers_wrong" rows={4} maxLength={4000} value={wrong} onChange={(e) => setWrong(e.target.value)} />
        </label>
        <label>
          What did you have to look up or answer outside the app?
          <textarea name="outside_questions" rows={3} maxLength={4000} value={outside} onChange={(e) => setOutside(e.target.value)} />
        </label>
        <label>
          What was missing?
          <textarea name="missing" rows={3} maxLength={4000} value={missing} onChange={(e) => setMissing(e.target.value)} />
        </label>
        <label className="fbshort">
          Minutes spent on this lot
          <input name="minutes_spent" inputMode="numeric" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
        </label>
        <fieldset>
          <legend>Would you use this for your own jobs?</legend>
          <div className="fbchoices">
            {(["yes", "maybe", "no"] as const).map((v) => (
              <label key={v}>
                <input type="radio" name="would_use" value={v} checked={wouldUse === v} onChange={() => setWouldUse(v)} />
                {v === "yes" ? "Yes" : v === "maybe" ? "Maybe" : "No"}
              </label>
            ))}
          </div>
        </fieldset>
        <label>
          Anything else
          <textarea name="notes" rows={3} maxLength={4000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        {signedInEmail ? (
          <p className="small muted">Sent as {signedInEmail}.</p>
        ) : (
          <label className="fbshort">
            Your email (so we can follow up)
            <input name="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
        )}
        <div className="bar">
          <button className="btn primary" type="submit" disabled={busy} data-testid="feedback-send">
            {busy ? "Sending..." : "Send"}
          </button>
          {pin && <Link href={`/parcels/${pin}/feasibility`}>Back to feasibility</Link>}
          {error && (
            <span className="err" role="alert">
              {error}
            </span>
          )}
        </div>
      </section>
    </form>
  );
}
