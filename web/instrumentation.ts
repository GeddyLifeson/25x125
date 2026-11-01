// Error tracking hook for the web app. With SENTRY_DSN set, server errors go to Sentry's envelope endpoint;
// without it, nothing is sent (Next.js still logs the error). No SDK needed.
export async function register() {}

type ErrorRequest = { path: string; method: string };

export async function onRequestError(err: unknown, request: ErrorRequest) {
  const dsn = process.env.SENTRY_DSN;
  if (!dsn) return;
  try {
    const u = new URL(dsn);
    const project = u.pathname.replace(/^\/+|\/+$/g, "").split("/").pop();
    if (!u.username || !project) return;
    const e = err instanceof Error ? err : new Error(String(err));
    const id = crypto.randomUUID().replace(/-/g, "");
    const event = JSON.stringify({
      event_id: id,
      timestamp: new Date().toISOString(),
      platform: "javascript",
      level: "error",
      environment: process.env.APP_ENV ?? "development",
      server_name: "web",
      exception: { values: [{ type: e.name, value: e.message, stacktrace: { frames: [] } }] },
      extra: { path: request.path, method: request.method, stack: e.stack?.slice(0, 4000) },
    });
    const body = `${JSON.stringify({ event_id: id })}\n${JSON.stringify({ type: "event", length: Buffer.byteLength(event) })}\n${event}\n`;
    await fetch(`${u.protocol}//${u.host}/api/${project}/envelope/`, {
      method: "POST",
      headers: {
        "content-type": "application/x-sentry-envelope",
        "x-sentry-auth": `Sentry sentry_version=7, sentry_key=${u.username}, sentry_client=x25x125-web/0.1`,
      },
      body,
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // a broken error tracker must not break the app
  }
}
