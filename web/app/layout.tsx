import type { ReactNode } from "react";

export const metadata = {
  title: "25x125",
  description: "What can be built on a Chicago parcel, what it costs, and whether it makes money.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0 }}>{children}</body>
    </html>
  );
}
