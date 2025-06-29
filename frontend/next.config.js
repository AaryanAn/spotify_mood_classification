/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // Enable static export for free deployment (Netlify/Vercel)
  output: process.env.STATIC_EXPORT === 'true' ? 'export' : undefined,
  trailingSlash: true,
  
  experimental: {
    appDir: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    // Skip rewrites for static export
    if (process.env.STATIC_EXPORT === 'true') {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
  images: {
    domains: ['i.scdn.co', 'mosaic.scdn.co', 'lineup-images.scdn.co'],
    // Disable image optimization for static export
    unoptimized: process.env.STATIC_EXPORT === 'true',
  },
};

module.exports = nextConfig; 