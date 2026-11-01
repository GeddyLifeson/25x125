import type { ReactNode } from "react";
import "./globals.css";
import { Nav } from "../components/Nav";

export const metadata = {
  title: "25x125",
  description: "What can be built on a Chicago parcel, what it costs, and whether it makes money.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
        <footer className="foot">
          Estimates, not tax, legal, zoning or appraisal advice. Data from the Chicago Data Portal, the Cook County data
          catalog, the U.S. Census Bureau and FHFA, copied nightly into the 25x125 database.
        </footer>
      </body>
    </html>
  );
}
