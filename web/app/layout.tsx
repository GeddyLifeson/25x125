import type { ReactNode } from "react";
import "./globals.css";
import { Nav } from "../components/Nav";
import { StaleDataNote } from "../components/StaleDataNote";
import { getSession, trialDaysLeft } from "../lib/session";

export const metadata = {
  title: "25x125",
  description: "What can be built on a Chicago parcel, what it costs, and whether it makes money.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const s = await getSession();
  const days = s ? trialDaysLeft(s.org) : null;
  const account = s ? { email: s.user.email, plan: days !== null ? `Pro trial, ${days} days left` : s.org.plan_label } : null;
  return (
    <html lang="en">
      <body>
        <Nav account={account} />
        <StaleDataNote />
        {children}
        <footer className="foot">
          Estimates, not tax, legal, zoning or appraisal advice. Data from the Chicago Data Portal, the Cook County data
          catalog, the U.S. Census Bureau and FHFA, copied nightly into the 25x125 database.
        </footer>
      </body>
    </html>
  );
}
