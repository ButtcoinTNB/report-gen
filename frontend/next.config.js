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
    minimumCacheTTL: 3600, // Increase cache time to 1 hour
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
  
  // Add optimized caching headers for production
  async headers() {
    return [
      {
        // Don't cache API responses
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, max-age=0',
          },
        ],
      },
      {
        // Cache static assets aggressively
        source: '/:path*(\.js|\.css|\.woff2|\.jpg|\.jpeg|\.png|\.gif|\.ico|\.svg)$',
        headers: [
          {
            key: 'Cache-Control',
            value: process.env.NODE_ENV === 'production'
              ? 'public, max-age=31536000, immutable' // 1 year for production
              : 'no-store, max-age=0', // No cache for development
          },
        ],
      },
      {
        // Default caching for HTML pages
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: process.env.NODE_ENV === 'production'
              ? 'public, max-age=3600, s-maxage=60, stale-while-revalidate=86400' // 1 hour with stale-while-revalidate
              : 'no-store, max-age=0', // No cache for development
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
  },
  // Enable Automatic Static Optimization where possible
  // This will pre-render pages to static HTML when possible
  experimental: {
    optimizeCss: true, // Optimize CSS
    optimizeImages: true, // Optimize images
    scrollRestoration: true, // Restore scroll position on navigation
    workerThreads: true, // Use worker threads for improved performance
  }
};

module.exports = withBundleAnalyzer(nextConfig); 