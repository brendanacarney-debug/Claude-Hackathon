import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, ".."),
  outputFileTracingIncludes: {
    "/*": ["../fixtures/demo_session.json", "../fixtures/demo_profiles.json"],
  },
};

export default nextConfig;
