/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    SUPABASE_URL: process.env.SUPABASE_URL || '',
    SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || '',
    BACKEND_URL: process.env.BACKEND_URL || process.env.STOKVIGIL_BACKEND_URL || '',
  },
};

module.exports = nextConfig;
