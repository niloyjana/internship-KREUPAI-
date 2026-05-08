/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@adwp/types', '@adwp/config'],
  async rewrites() {
    return [
      { source: '/api/auth/:path*', destination: 'http://localhost:3009/v1/auth/:path*' },
      { source: '/api/tenants/:path*', destination: 'http://localhost:3002/v1/tenants/:path*' },
      { source: '/api/agents/:path*', destination: 'http://localhost:3003/v1/agents/:path*' },
      { source: '/api/workflows/:path*', destination: 'http://localhost:3004/v1/workflows/:path*' },
      {
        source: '/api/subscriptions/:path*',
        destination: 'http://localhost:3005/v1/subscriptions/:path*',
      },
      {
        source: '/api/integrations/:path*',
        destination: 'http://localhost:3006/v1/integrations/:path*',
      },
      { source: '/api/analytics/:path*', destination: 'http://localhost:3007/v1/analytics/:path*' },
      {
        source: '/api/notifications/:path*',
        destination: 'http://localhost:3008/v1/notifications/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
