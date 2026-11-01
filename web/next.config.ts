import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The engine runs separately (FastAPI). Screens call it through ENGINE_URL.
  // The PDF renderer is plain JavaScript; keep it out of the server bundle so its font files load at run time.
  serverExternalPackages: ["@react-pdf/renderer"],
};

export default nextConfig;
