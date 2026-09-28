import type { NextConfig } from 'next';
import path from 'node:path';
const nextConfig: NextConfig = {
  distDir: process.env.IRIS_NEXT_DIST || '.next',
  outputFileTracingRoot: path.resolve(process.cwd()),
  async rewrites() {
    if (process.env.BACKEND_URL) {
      return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL}/api/:path*` }];
    }
    return [];
  },
};
export default nextConfig;
