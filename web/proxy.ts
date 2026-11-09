// Sign-in walls and a same-origin check for changes. The real checks happen in the engine; this only sends
// signed-out visitors to the sign-in page early.
import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "x25_session";
const PROTECTED = [/^\/deals(\/|$)/, /^\/account(\/|$)/];

// The public website (Hugging Face Space, docs/website.md) runs in single-user mode, so SITE_PASSWORD keeps
// strangers out: every page asks for it once, then a cookie remembers it for 90 days.
const GATE_COOKIE = "x25_gate";
const GATE_DAYS = 90;

async function gateToken(password: string): Promise<string> {
  const data = new TextEncoder().encode(`x25-gate:${password}`);
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", data));
  return Array.from(hash, (b) => b.toString(16).padStart(2, "0")).join("");
}

function unlockPage(next: string, wrong: boolean, status = 200): NextResponse {
  const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
  const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>25x125</title><style>body{font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:90vh;margin:0 16px;color:#222}
form{display:grid;gap:12px;width:100%;max-width:320px}input,button{font:inherit;padding:10px;border:1px solid #bbb;border-radius:6px}
button{background:#222;color:#fff;border-color:#222;cursor:pointer}.err{color:#b00020}</style></head><body>
<form method="post" action="/unlock"><h1>25x125</h1><label>Password<br><input type="password" name="password" autofocus required style="width:100%;box-sizing:border-box"></label>
<input type="hidden" name="next" value="${esc(next)}">${wrong ? '<p class="err">That password is wrong.</p>' : ""}
<button type="submit">Open</button></form></body></html>`;
  return new NextResponse(html, { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

async function gate(req: NextRequest, password: string): Promise<NextResponse | null> {
  const { pathname, search } = req.nextUrl;
  const token = await gateToken(password);
  if (pathname === "/unlock") {
    if (req.method !== "POST") return unlockPage(req.nextUrl.searchParams.get("next") ?? "/", false);
    const form = await req.formData();
    const next = String(form.get("next") ?? "/");
    const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/";
    if (String(form.get("password") ?? "") !== password) return unlockPage(safeNext, true, 401);
    const res = NextResponse.redirect(new URL(safeNext, req.url), 303);
    res.cookies.set(GATE_COOKIE, token, {
      httpOnly: true,
      secure: req.nextUrl.protocol === "https:" || req.headers.get("x-forwarded-proto") === "https",
      sameSite: "lax",
      path: "/",
      maxAge: GATE_DAYS * 86400,
    });
    return res;
  }
  if (req.cookies.get(GATE_COOKIE)?.value === token) return null;
  if (pathname.startsWith("/api/") || req.method !== "GET") {
    return new NextResponse("Password needed.", { status: 401 });
  }
  return unlockPage(pathname + search, false);
}

export async function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const sitePassword = process.env.SITE_PASSWORD;
  if (sitePassword) {
    const blocked = await gate(req, sitePassword);
    if (blocked) return blocked;
  }
  if (pathname.startsWith("/api/") && !["GET", "HEAD", "OPTIONS"].includes(req.method) && pathname !== "/api/billing/webhook") {
    const origin = req.headers.get("origin");
    // Behind a port forwarder (GitHub Codespaces) the browser's address differs from the Host header the app
    // sees, so APP_ORIGINS lists the extra hosts allowed to send changes (comma-separated, e.g.
    // name-3000.app.github.dev). scripts/codespace.py sets it.
    const allowed = [req.headers.get("host"), ...(process.env.APP_ORIGINS ?? "").split(",").map((h) => h.trim())];
    if (origin && !allowed.includes(new URL(origin).host)) {
      return new NextResponse("Cross-site request refused.", { status: 403 });
    }
  }
  // Desktop mode (LOCAL_MODE=1) has no sign-in: the engine treats every call as the one local user.
  const local = process.env.LOCAL_MODE === "1" && process.env.APP_ENV !== "production";
  if (local && pathname === "/signin") return NextResponse.redirect(new URL("/", req.url));
  if (!local && PROTECTED.some((r) => r.test(pathname)) && !req.cookies.get(SESSION_COOKIE)) {
    const url = req.nextUrl.clone();
    url.pathname = "/signin";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

// Every path but the build's static files, so the site password (above) covers pages, data and map tiles.
export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
