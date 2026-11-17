"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { SAMPLE_ADDRESS, SAMPLE_PIN } from "../lib/sample";

const KEY = "x25_guide_closed";

/** A one-line guide on the first visit to the search screen. Closing it is remembered in this browser. */
export function FirstVisitGuide() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      setShow(window.localStorage.getItem(KEY) !== "1");
    } catch {
      setShow(true);
    }
  }, []);
  if (!show) return null;
  const close = () => {
    setShow(false);
    try {
      window.localStorage.setItem(KEY, "1");
    } catch {
      // private window: the guide shows again next time
    }
  };
  return (
    <div className="guide" role="note" data-testid="guide">
      <span>
        <b>New here?</b> Pick an area or a lot from the list, open its parcel page, then run feasibility.
      </span>
      <Link href={`/parcels/${SAMPLE_PIN}`}>Try the sample lot: {SAMPLE_ADDRESS}</Link>
      <Link href="/search">Check an address</Link>
      <Link href="/help">How it works</Link>
      <button type="button" onClick={close}>
        Close
      </button>
    </div>
  );
}
