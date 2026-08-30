import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/:path*", // Proxy to FastAPI
      },
      {
        source: "/outputs/:path*",
        destination: "http://127.0.0.1:8000/outputs/:path*", // Proxy to FastAPI outputs
      },
      {
        source: "/uploads/:path*",
        destination: "http://127.0.0.1:8000/uploads/:path*", // Proxy to FastAPI uploads
      },
    ];
  },
};

export default nextConfig;
