const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";

async function engineStatus(): Promise<string> {
  try {
    const res = await fetch(`${ENGINE_URL}/health`, { cache: "no-store" });
    const body = (await res.json()) as { status: string; postgis?: string };
    return body.status === "ok" ? `Engine ok, PostGIS ${body.postgis}` : `Engine: ${body.status}`;
  } catch {
    return "Engine not running";
  }
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const status = await engineStatus();
  return (
    <main style={{ padding: 24, maxWidth: 720 }}>
      <h1>25x125</h1>
      <p>Search, parcel and feasibility screens arrive in steps 5 and 6.</p>
      <p>{status}</p>
    </main>
  );
}
