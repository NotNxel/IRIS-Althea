import type { NextConfig } from 'next';
import path from 'node:path';
const nextConfig: NextConfig = {
  distDir: process.env.IRIS_NEXT_DIST || '.next',
  outputFileTracingRoot: path.resolve(process.cwd()),
  async rewrites() { return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL || 'http://127.0.0.1:8000'}/api/:path*` }]; },
};
export default nextConfig;
