import type { ReactNode } from "react";

/** A small "source" disclosure for one number: where it came from and when (CLAUDE.md rule 2). */
export function Source({ label = "source", children }: { label?: string; children: ReactNode }) {
  return (
    <details className="src">
      <summary>{label}</summary>
      <span className="body">{children}</span>
    </details>
  );
}
