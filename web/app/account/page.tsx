import { redirect } from "next/navigation";
import { getAccount, getAuditLog, getBillingPlans, getSavedSearches, settle } from "../../lib/engine";
import { getSession, trialDaysLeft } from "../../lib/session";
import { AccountScreen } from "./AccountScreen";

export const dynamic = "force-dynamic";
export const metadata = { title: "Account · 25x125" };

type Props = { searchParams: Promise<{ need?: string; billing?: string; billing_error?: string }> };

export default async function AccountPage({ searchParams }: Props) {
  const sp = await searchParams;
  const session = await getSession();
  if (!session) redirect("/signin?next=/account");
  const acct = await settle(getAccount());
  if (!acct.ok) {
    return (
      <main className="wrap">
        <h1>Account</h1>
        <p className="err">Could not load the account: {acct.error}</p>
      </main>
    );
  }
  const isPro = acct.value.org.features.includes("saved_searches");
  const [plans, searches, audit] = await Promise.all([
    settle(getBillingPlans()),
    isPro ? settle(getSavedSearches()) : Promise.resolve(null),
    acct.value.org.role === "owner" ? settle(getAuditLog(50)) : Promise.resolve(null),
  ]);
  return (
    <AccountScreen
      account={acct.value}
      orgs={session.orgs}
      trialDaysLeft={trialDaysLeft(acct.value.org)}
      billingReady={plans.ok ? Boolean(plans.value.billing_ready) : false}
      searches={searches?.ok ? searches.value : null}
      audit={audit?.ok ? audit.value : null}
      need={sp.need ?? null}
      billingNote={sp.billing_error ? `Billing: ${sp.billing_error}` : sp.billing === "done" ? "Thanks. Stripe confirms the plan in a few seconds; reload to see it." : null}
    />
  );
}
