"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Nav() {
  const path = usePathname() ?? "/";
  const m = path.match(/^\/parcels\/(\d+)/);
  const pin = m?.[1];
  const onFeas = path.endsWith("/feasibility");
  return (
    <header className="top">
      <Link href="/" className="brand">
        <b>25x125</b>
        <span>Chicago development pipeline</span>
      </Link>
      <nav aria-label="Screens">
        <Link href="/map" className={path === "/map" ? "on" : undefined}>
          Map and list
        </Link>
        <Link href="/" className={path === "/" ? "on" : undefined}>
          Address search
        </Link>
        {pin ? (
          <Link href={`/parcels/${pin}`} className={!onFeas ? "on" : undefined}>
            Parcel
          </Link>
        ) : (
          <span>Parcel</span>
        )}
        {pin ? (
          <Link href={`/parcels/${pin}/feasibility`} className={onFeas ? "on" : undefined}>
            Feasibility
          </Link>
        ) : (
          <span>Feasibility</span>
        )}
        <Link href="/deals" className={path === "/deals" ? "on" : undefined}>
          Deals
        </Link>
      </nav>
      <div className="note">Every number is an estimate and can be edited</div>
    </header>
  );
}
