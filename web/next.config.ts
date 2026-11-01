import path from "node:path";
import type { NextConfig } from "next";

// The app reads rule files from ../data/rules, so the bundler's root is the repo root, not web/.
const repoRoot = path.join(__dirname, "..");

const nextConfig: NextConfig = {
  // The engine runs separately (FastAPI). Screens call it through ENGINE_URL.
  // The PDF renderer is plain JavaScript; keep it out of the server bundle so its font files load at run time.
  serverExternalPackages: ["@react-pdf/renderer"],
  turbopack: { root: repoRoot },
  outputFileTracingRoot: repoRoot,
  // The production image (deploy/web.Dockerfile) sets NEXT_OUTPUT=standalone: a self-contained server in
  // .next/standalone. Left unset, `npm run build` and `npm run start` work as before.
  ...(process.env.NEXT_OUTPUT === "standalone" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
