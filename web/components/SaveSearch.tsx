"use client";
import Link from "next/link";
import { useState } from "react";

/** Save the map's current filters by name (Pro). Alerts on saved searches come in version 1.1. */
export function SaveSearch({ params, suggested }: { params: string; suggested: string }) {
  const [state, setState] = useState<{ ok?: string; wall?: number; err?: string } | null>(null);
  if (state?.wall === 401) {
    return (
      <Link className="btn small" href={`/signin?next=${encodeURIComponent(`/map?${params}`)}`}>
        Sign in to save searches
      </Link>
    );
  }
  if (state?.wall === 402) {
    return (
      <Link className="btn small" href="/account">
        Saved searches are part of Pro
      </Link>
    );
  }
  return (
    <>
      <button
        className="btn small"
        type="button"
        data-testid="save-search"
        onClick={async () => {
          const name = window.prompt("Name this search", suggested);
          if (!name) return;
          const res = await fetch("/api/saved-searches", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ name, params }),
          });
          if (res.status === 401 || res.status === 402) return setState({ wall: res.status });
          const body = (await res.json()) as { detail?: string };
          setState(res.ok ? { ok: `Saved "${name}"` } : { err: body.detail ?? res.statusText });
        }}
      >
        Save search
      </button>
      {state?.ok && (
        <span className="small" role="status" data-testid="search-saved">
          {state.ok}. <Link href="/account">Saved searches</Link>
        </span>
      )}
      {state?.err && <span className="err">{state.err}</span>}
    </>
  );
}
