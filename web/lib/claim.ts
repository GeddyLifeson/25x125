// Signed claims for engine calls (server side only). The engine checks the HMAC with the same
// ENGINE_SHARED_SECRET and rejects organization data requests without a valid one (engine/auth.py).
import { createHmac } from "node:crypto";

export const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";
export const CLAIM_HEADER = "x-25x125-claim";
// Same fallback as the engine, for local work only. Production (APP_ENV=production) must set the secret.
const DEV_SECRET = "dev-only-shared-secret-not-for-production";

export const isProduction = () => process.env.APP_ENV === "production";
/** Single-user desktop mode (desktop/): no sign-in, the engine treats every call as the local user on Pro. */
export const isLocal = () => process.env.LOCAL_MODE === "1" && !isProduction();

function secret(): string {
  const s = process.env.ENGINE_SHARED_SECRET;
  if (s) return s;
  if (isProduction()) throw new Error("ENGINE_SHARED_SECRET is not set on the web app");
  return DEV_SECRET;
}

export type Claim = { uid: string | null; org: string | null; ip: string };

/** Header value: base64url(JSON claim with a 60-second expiry) + "." + base64url(HMAC-SHA256). */
export function signClaim(c: Claim): string {
  const body = Buffer.from(JSON.stringify({ ...c, exp: Math.floor(Date.now() / 1000) + 60 })).toString("base64url");
  const sig = createHmac("sha256", secret()).update(body).digest("base64url");
  return `${body}.${sig}`;
}
