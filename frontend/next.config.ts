import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // バックエンド API へのリバースプロキシ（開発時）
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
