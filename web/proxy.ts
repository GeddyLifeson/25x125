// Sign-in walls and a same-origin check for changes. The real checks happen in the engine; this only sends
// signed-out visitors to the sign-in page early.
import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "x25_session";
const PROTECTED = [/^\/deals(\/|$)/, /^\/account(\/|$)/];

export function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (pathname.startsWith("/api/") && !["GET", "HEAD", "OPTIONS"].includes(req.method) && pathname !== "/api/billing/webhook") {
    const origin = req.headers.get("origin");
    if (origin && new URL(origin).host !== req.headers.get("host")) {
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

export const config = { matcher: ["/deals", "/deals/:path*", "/account", "/account/:path*", "/api/:path*", "/signin"] };
