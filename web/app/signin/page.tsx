import Link from "next/link";
import { ENGINE_URL } from "../../lib/claim";
import { getSession } from "../../lib/session";
import { SignInForm } from "./SignInForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sign in · 25x125" };

type Props = { searchParams: Promise<{ next?: string; email?: string; error?: string }> };

async function devMode(): Promise<boolean> {
  try {
    const res = await fetch(`${ENGINE_URL}/auth/config`, { cache: "no-store" });
    return ((await res.json()) as { email_dev_mode: boolean }).email_dev_mode;
  } catch {
    return false;
  }
}

export default async function SignInPage({ searchParams }: Props) {
  const sp = await searchParams;
  const next = sp.next && sp.next.startsWith("/") && !sp.next.startsWith("//") ? sp.next : "/";
  const [session, dev] = await Promise.all([getSession(), devMode()]);
  return (
    <main className="wrap" style={{ maxWidth: 560 }}>
      <section className="card">
        <h1 style={{ fontSize: 24, marginBottom: 6 }}>Sign in</h1>
        {session ? (
          <p>
            Signed in as <b>{session.user.email}</b>. <Link href={next}>Continue</Link> or open your{" "}
            <Link href="/account">account</Link>.
          </p>
        ) : (
          <>
            <p className="muted" style={{ marginBottom: 14 }}>
              Enter your email. We send a link that signs you in; there is no password. New accounts start with 14 days of
              Pro. Search, the parcel page, the map and the feasibility screen work without an account.
            </p>
            {sp.error && <p className="err">{sp.error}</p>}
            <SignInForm next={next} email={sp.email ?? ""} />
            {dev && (
              <p className="small muted" style={{ marginTop: 12 }} data-testid="dev-mode">
                Dev mode: EMAIL_SERVER is not set on the engine, so no email is sent. The sign-in link is printed in the engine
                console and saved in <span className="mono">.dev-mail/</span> in the repo folder.
              </p>
            )}
          </>
        )}
      </section>
    </main>
  );
}
