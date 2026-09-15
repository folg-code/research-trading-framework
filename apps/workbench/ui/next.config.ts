import path from "node:path";
import type { NextConfig } from "next";

// ADR-0044: static export only. No Next.js server process ever runs -- no
// API routes, no SSR, no middleware. `workbench-api` serves the built
// `out/` directory itself; see apps/workbench/CLAUDE.md.
const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  turbopack: {
    // Pins the project root to this directory -- without it, Turbopack
    // walks up looking for a lockfile and can land outside the repo
    // entirely on a machine with an unrelated package-lock.json higher up.
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
