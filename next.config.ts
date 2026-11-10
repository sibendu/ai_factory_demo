import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingExcludes: {
    "/*": ["./config/users.local.json", "./.env*"],
  },
};

export default nextConfig;
