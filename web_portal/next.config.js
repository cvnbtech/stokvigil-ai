/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    SUPABASE_URL: process.env.SUPABASE_URL || '',
    SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || '',
    STOKVIGIL_BACKEND_URL: process.env.STOKVIGIL_BACKEND_URL || '',
  },
  async rewrites() {
    const backendUrl = (process.env.STOKVIGIL_BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '');
    return [
      {
        source: '/api/stocks/:path*',
        destination: `${backendUrl}/api/stocks/:path*`,
      },
      {
        source: '/api/user/:path*',
        destination: `${backendUrl}/api/user/:path*`,
      },
      {
        source: '/api/auth/register-device',
        destination: `${backendUrl}/api/auth/register-device`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/health`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'Content-Security-Policy',
            value: "frame-ancestors 'none';",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;

