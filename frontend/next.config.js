/** @type {import('next').NextConfig} */
const nextConfig = {
  // Prevent 308 slash redirects that drop POST bodies for /api/*
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const api = process.env.API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*/",
        destination: `${api}/api/:path*/`,
      },
      {
        source: "/api/:path*",
        destination: `${api}/api/:path*/`,
      },
    ];
  },
};

module.exports = nextConfig;
