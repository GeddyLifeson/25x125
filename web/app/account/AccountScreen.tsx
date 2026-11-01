"use client";
import Link from "next/link";
import { useState } from "react";
import type { AccountView, AuditRow } from "../../lib/engine";
import type { SavedSearch } from "../../lib/types";

type Props = {
  account: AccountView;
  orgs: { id: string; name: string; role: string }[];
  trialDaysLeft: number | null;
  billingReady: boolean;
  searches: SavedSearch[] | null;
  audit: AuditRow[] | null;
  need: string | null;
  billingNote: string | null;
};

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`/api/${path}`, init);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? res.statusText);
  }
  return res.status === 204 ? null : res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export function AccountScreen(props: Props) {
  const { account } = props;
  const org = account.org;
  const pro = account.plans.plans.pro;
  const isOwner = org.role === "owner";
  const [members, setMembers] = useState(account.members);
  const [invites, setInvites] = useState(account.invites);
  const [searches, setSearches] = useState(props.searches);
  const [invite, setInvite] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(props.billingNote);
  const [err, setErr] = useState<string | null>(null);
  const run = (f: () => Promise<void>) => () => {
    setErr(null);
    f().catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e)));
  };

  const planLine =
    org.plan_status === "trialing" && props.trialDaysLeft !== null
      ? `Pro trial: ${props.trialDaysLeft} day${props.trialDaysLeft === 1 ? "" : "s"} left`
      : org.plan_status === "comp"
        ? "Pro (no charge)"
        : org.plan === "pro"
          ? `Pro${org.founding ? " (founding price)" : ""}, ${org.plan_status.replace("_", " ")}`
          : "Free";
  const price = org.founding && pro.founding_price_month ? pro.founding_price_month : pro.price_month;

  return (
    <main className="wrap" style={{ maxWidth: 960 }}>
      <div className="head">
        <div>
          <h1>Account</h1>
          <p className="muted">
            {account.user.email} · {org.name} ({org.role})
          </p>
        </div>
        <form action="/api/auth/signout" method="post">
          <button className="btn small" type="submit" data-testid="sign-out">
            Sign out
          </button>
        </form>
      </div>
      {msg && (
        <p className="small" role="status">
          {msg}
        </p>
      )}
      {err && <p className="err">{err}</p>}
      {props.need === "exports" && (
        <p className="err">PDF and CSV exports are part of Pro. Your deals and edits are kept while you decide.</p>
      )}

      <section className="card" data-testid="plan">
        <h2>Plan</h2>
        <p>
          <b data-testid="plan-line">{planLine}</b>
          {org.current_period_end && org.plan_status === "active" && <> · renews {org.current_period_end.slice(0, 10)}</>}
        </p>
        <p className="small muted">
          Pro: ${price} a month{org.founding ? " (founding price; list price $" + pro.price_month + ")" : ""}, sales tax added
          where it applies. {pro.summary} Free: {account.plans.plans.free.summary}
        </p>
        <p className="small muted">
          Prices as of {account.plans.verified_on}.
        </p>
        {isOwner ? (
          <div className="bar" style={{ marginTop: 10 }}>
            {org.plan_status !== "active" && org.plan_status !== "comp" && (
              <form action="/api/billing/checkout" method="post">
                <button className="btn primary small" type="submit" disabled={!props.billingReady}>
                  {org.plan_status === "trialing" ? "Add a card to keep Pro after the trial" : "Start Pro"}
                </button>
              </form>
            )}
            {org.has_billing && (
              <form action="/api/billing/portal" method="post">
                <button className="btn small" type="submit" disabled={!props.billingReady}>
                  Invoices, card and cancel
                </button>
              </form>
            )}
          </div>
        ) : (
          <p className="small muted">The owner manages billing.</p>
        )}
        {!props.billingReady && (
          <p className="small muted" style={{ marginTop: 8 }}>
            Billing is not set up on this server yet (Stripe keys are empty). The trial works without it.
          </p>
        )}
      </section>

      {props.orgs.length > 1 && (
        <section className="card">
          <h2>Organizations</h2>
          <div className="bar">
            {props.orgs.map((o) => (
              <button
                key={o.id}
                className={`btn small${o.id === org.id ? " primary" : ""}`}
                type="button"
                onClick={run(async () => {
                  await api("auth/switch-org", json("POST", { org_id: o.id }));
                  window.location.reload();
                })}
              >
                {o.name} ({o.role})
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="card">
        <h2>Team</h2>
        <p className="small muted">One owner per team. Teammates see and edit the same deals, saved edits and searches.</p>
        <table className="t">
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.email}</td>
                <td>{m.role}</td>
                <td className="muted">since {m.since}</td>
                <td>
                  {isOwner && m.role !== "owner" && (
                    <button
                      className="btn small"
                      type="button"
                      onClick={run(async () => {
                        await api(`account/members/${m.id}`, { method: "DELETE" });
                        setMembers(members.filter((x) => x.id !== m.id));
                      })}
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {invites.map((i) => (
              <tr key={`i${i.id}`}>
                <td>{i.email}</td>
                <td className="muted">invited {i.sent}</td>
                <td className="muted">expires {i.expires}</td>
                <td>
                  {isOwner && (
                    <button
                      className="btn small"
                      type="button"
                      onClick={run(async () => {
                        await api(`account/invites/${i.id}`, { method: "DELETE" });
                        setInvites(invites.filter((x) => x.id !== i.id));
                      })}
                    >
                      Cancel invite
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {isOwner && org.features.includes("invites") && (
          <form
            className="search"
            style={{ marginTop: 10 }}
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                const r = (await api("account/invites", json("POST", { email: invite }))) as { id: number; email: string; sent: boolean };
                setInvites([...invites, { id: r.id, email: r.email, sent: new Date().toISOString().slice(0, 10), expires: "in 14 days" }]);
                setInvite("");
                setMsg(r.sent ? `Invite sent to ${r.email}.` : `Invite saved for ${r.email} (dev mode: the email is in .dev-mail/).`);
              })();
            }}
          >
            <input type="email" required value={invite} onChange={(e) => setInvite(e.target.value)} placeholder="teammate@company.com" aria-label="Invite by email" />
            <button className="btn small" type="submit">
              Invite
            </button>
          </form>
        )}
      </section>

      <section className="card">
        <h2>Saved searches</h2>
        {searches === null ? (
          <p className="small muted">Saved searches are part of Pro.</p>
        ) : searches.length === 0 ? (
          <p className="small muted">
            None yet. Save one from the <Link href="/map">map and list</Link>.
          </p>
        ) : (
          <ul className="plain" data-testid="saved-searches">
            {searches.map((s) => (
              <li key={s.id}>
                <Link href={`/map?${s.params}`}>{s.name}</Link>{" "}
                <button
                  className="btn small"
                  type="button"
                  onClick={run(async () => {
                    await api(`saved-searches/${s.id}`, { method: "DELETE" });
                    setSearches(searches.filter((x) => x.id !== s.id));
                  })}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {props.audit && (
        <section className="card">
          <h2>Audit log</h2>
          <p className="small muted">Saved edits, deal changes, exports and account changes in this organization, newest first (last 50).</p>
          <div className="scroll">
            <table className="t" data-testid="audit">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>What</th>
                  <th>On</th>
                </tr>
              </thead>
              <tbody>
                {props.audit.map((a, i) => (
                  <tr key={i}>
                    <td className="mono small">{a.at.slice(0, 16).replace("T", " ")}</td>
                    <td>{a.who ?? "deleted user"}</td>
                    <td className="mono small">{a.action}</td>
                    <td>{a.target ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="card">
        <h2>Delete account</h2>
        <p className="small muted">
          Deletes your sign-in{isOwner ? `, and ${org.name} with all its deals, outreach log, saved edits, saved searches and audit log` : ""}.
          {isOwner && members.length > 1 ? " Teammates keep their own sign-in but lose this organization's data." : ""} This cannot be undone.
          Export your deals as CSV first if you want a copy.
        </p>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await api(`account?confirm=${encodeURIComponent(confirm)}`, { method: "DELETE" });
              window.location.href = "/";
            })();
          }}
        >
          <input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Type your email to confirm" aria-label="Confirm email" data-testid="delete-confirm" />
          <button className="btn small" type="submit" disabled={confirm.trim().toLowerCase() !== account.user.email} data-testid="delete-account">
            Delete my account
          </button>
        </form>
      </section>
    </main>
  );
}
