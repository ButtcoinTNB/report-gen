/** @type {import('next').NextConfig} */
const withBundleAnalyzer = process.env.ANALYZE === 'true' ? 
  require('@next/bundle-analyzer')({ enabled: true }) : 
  (config) => config;

const nextConfig = {
  reactStrictMode: true,
  // Specify which file extensions to use for Pages Router
  pageExtensions: ['tsx', 'ts', 'jsx', 'js'],
  // ESLint configuration
  eslint: {
    // Warning instead of error for production builds
    ignoreDuringBuilds: true,
  },
  // Image optimization
  images: {
    domains: ['jkvmxxdshxyjhdoszrkv.supabase.co'],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60,
  },
  // Performance optimizations
  swcMinify: true, // Use SWC for minification (faster than Terser)
  compiler: {
    // Remove console.log in production but keep error and warn for debugging
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
  // Output standalone build for better deployment performance
  output: 'standalone',
  
  // Add headers to prevent caching during development
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, max-age=0',
          },
        ],
      },
    ];
  },
  typescript: {
    // This allows the build to succeed even with TypeScript errors
    ignoreBuildErrors: true,
  },
  webpack: (config, { isServer }) => {
    // Only include specific polyfills or packages on the server
    if (!isServer) {
      // Don't bundle server-only dependencies on the client
    }
    return config;
  }
};

module.exports = withBundleAnalyzer(nextConfig); 