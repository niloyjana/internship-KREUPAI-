/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@adwp/types', '@adwp/config'],
  async rewrites() {
    return [
      { source: '/api/v1/auth/:path*', destination: 'http://localhost:3009/v1/auth/:path*' },
      { source: '/api/v1/tenants/:path*', destination: 'http://localhost:3002/v1/tenants/:path*' },
      { source: '/api/v1/agents/:path*', destination: 'http://localhost:3003/v1/agents/:path*' },
      {
        source: '/api/v1/workflows/:path*',
        destination: 'http://localhost:3004/v1/workflows/:path*',
      },
      {
        source: '/api/v1/subscriptions/:path*',
        destination: 'http://localhost:3005/v1/subscriptions/:path*',
      },
      {
        source: '/api/v1/integrations/:path*',
        destination: 'http://localhost:3006/v1/integrations/:path*',
      },
      {
        source: '/api/v1/analytics/:path*',
        destination: 'http://localhost:3007/v1/analytics/:path*',
      },
      {
        source: '/api/v1/notifications/:path*',
        destination: 'http://localhost:3008/v1/notifications/:path*',
      },
      {
        source: '/api/v1/runtime/:path*',
        destination: 'http://localhost:8000/v1/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
