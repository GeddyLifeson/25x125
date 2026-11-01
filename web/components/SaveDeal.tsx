"use client";
import Link from "next/link";
import { useState } from "react";

/** "Save to deals" on the parcel page: stores the lot as a lead; the nightly numbers show until feasibility is saved. */
export function SaveDeal({ pin }: { pin: string }) {
  const [id, setId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (id) {
    return (
      <Link className="btn" href={`/deals?d=${id}`}>
        Saved as deal {id}
      </Link>
    );
  }
  return (
    <>
      <button
        className="btn"
        type="button"
        onClick={async () => {
          const res = await fetch("/api/deals", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ pin, stage: "lead" }),
          });
          const body = (await res.json()) as { id?: number; detail?: string };
          if (res.ok && body.id) setId(body.id);
          else setErr(body.detail ?? res.statusText);
        }}
      >
        Save to deals
      </button>
      {err && <span className="err">{err}</span>}
    </>
  );
}
