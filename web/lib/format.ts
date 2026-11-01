// Number formatting. Costs are dollars with dollar margins, never a percent band (CLAUDE.md rule 3).

export function usd(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
  const r = Math.round(n);
  return (r < 0 ? "-$" : "$") + Math.abs(r).toLocaleString("en-US");
}

/** Short dollars for cards: $1,375k, $1.4M stays exact enough to read. */
export function usdK(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
  const a = Math.abs(n);
  const sign = n < 0 ? "-$" : "$";
  if (a >= 1_000_000) return `${sign}${(a / 1_000_000).toFixed(2)}M`;
  return `${sign}${Math.round(a / 1000).toLocaleString("en-US")}k`;
}

/** `$1,375,000 (-$275,000 / +$413,000)` from a central figure and its low and high. */
export function usdRange(central: number, low: number, high: number): string {
  const lo = Math.round(low - central);
  const hi = Math.round(high - central);
  if (lo === 0 && hi === 0) return usd(central);
  const signed = (d: number) => (d < 0 ? "-" : "+") + usd(Math.abs(d));
  return `${usd(central)} (${signed(lo)} / ${signed(hi)})`;
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
  return `${(n * 100).toFixed(digits)}%`;
}

export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function sqft(n: number | null | undefined): string {
  return n === null || n === undefined ? "n/a" : `${num(n)} sq ft`;
}

/** 16012160310000 -> 16-01-216-031-0000 */
export function formatPin(pin: string): string {
  const d = pin.replace(/\D/g, "");
  if (d.length === 14) return `${d.slice(0, 2)}-${d.slice(2, 4)}-${d.slice(4, 7)}-${d.slice(7, 10)}-${d.slice(10)}`;
  if (d.length === 10) return `${d.slice(0, 2)}-${d.slice(2, 4)}-${d.slice(4, 7)}-${d.slice(7, 10)}`;
  return pin;
}

export function titleCase(s: string | null | undefined): string {
  if (!s) return "";
  return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase());
}

export function day(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 10) : "n/a";
}

export function feet(n: number | null | undefined): string {
  if (n === null || n === undefined) return "n/a";
  return n >= 5280 ? `${(n / 5280).toFixed(2)} mi` : `${num(n)} ft`;
}
