"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export type NavAccount = { email: string; plan: string; isAdmin?: boolean; local?: boolean } | null;

export function Nav({ account }: { account?: NavAccount }) {
  const path = usePathname() ?? "/";
  const m = path.match(/^\/parcels\/(\d+)/);
  const pin = m?.[1];
  const onFeas = path.endsWith("/feasibility");
  const onSearch = path === "/" || path === "/map" || path === "/search";
  return (
    <header className="top">
      <Link href="/" className="brand">
        <b>25x125</b>
        <span>Chicago development pipeline</span>
      </Link>
      <nav aria-label="Screens">
        <Link href="/" className={onSearch ? "on" : undefined}>
          Search
        </Link>
        {pin ? (
          <Link href={`/parcels/${pin}`} className={!onFeas ? "on" : undefined}>
            Parcel
          </Link>
        ) : (
          <span title="Pick a lot from the search list first">Parcel</span>
        )}
        {pin ? (
          <Link href={`/parcels/${pin}/feasibility`} className={onFeas ? "on" : undefined}>
            Feasibility
          </Link>
        ) : (
          <span title="Pick a lot from the search list first">Feasibility</span>
        )}
        <Link href="/deals" className={path === "/deals" ? "on" : undefined}>
          Deals
        </Link>
      </nav>
      <div className="note">
        <Link href={path === "/feedback" ? "/feedback" : `/feedback?from=${encodeURIComponent(path)}`} data-testid="nav-feedback">
          Feedback
        </Link>
        {account?.isAdmin && (
          <Link href="/admin/feedback" data-testid="nav-admin">
            Feedback received
          </Link>
        )}
        {account?.local ? (
          <span data-testid="nav-local">This computer only</span>
        ) : account ? (
          <Link href="/account" data-testid="nav-account">
            {account.email} ({account.plan})
          </Link>
        ) : (
          <Link href={`/signin?next=${encodeURIComponent(path)}`} data-testid="nav-signin">
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
