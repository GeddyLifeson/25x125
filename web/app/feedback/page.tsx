import { getParcel, settle } from "../../lib/engine";
import { snapshotFromParams } from "../../lib/feedback";
import { formatPin, titleCase } from "../../lib/format";
import { getSession } from "../../lib/session";
import { FeedbackForm } from "./FeedbackForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "Check the numbers · 25x125" };

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default async function FeedbackPage({ searchParams }: Props) {
  const sp = await searchParams;
  const pinRaw = (one(sp.pin) ?? "").replace(/\D/g, "");
  const pin = pinRaw.length === 10 || pinRaw.length === 14 ? pinRaw : null;
  const sc = one(sp.scenario)?.toUpperCase();
  const scenario = sc === "A" || sc === "B" || sc === "C" ? sc : null;
  const from = one(sp.from);
  const pagePath = from && from.startsWith("/") && !from.startsWith("//") ? from.slice(0, 300) : null;
  const snapshot = snapshotFromParams(sp);
  const session = await getSession();
  let address = snapshot.address ?? null;
  if (pin && !address) {
    const p = await settle(getParcel(pin));
    if (p.ok) address = titleCase(p.value.address) || null;
  }
  if (address) snapshot.address = address;
  return (
    <main className="wrap" style={{ maxWidth: 960 }}>
      <section className="head">
        <div>
          <h1>{pin ? "Check these numbers" : "Feedback"}</h1>
          <span className="muted">
            {pin
              ? `${address ?? formatPin(pin)} · PIN ${formatPin(pin)}${scenario ? ` · scenario ${snapshot.scenario_name ?? scenario}` : ""}`
              : "Tell us what looked wrong, what you had to look up elsewhere, and what was missing."}
          </span>
        </div>
      </section>
      <FeedbackForm
        pin={pin}
        scenario={scenario}
        pagePath={pagePath ?? (pin ? `/parcels/${pin}/feasibility` : null)}
        snapshot={snapshot}
        signedInEmail={session?.user.email ?? null}
      />
    </main>
  );
}
