/** @type {import('next').NextConfig} */
const withBundleAnalyzer = process.env.ANALYZE === 'true' ? 
  require('@next/bundle-analyzer')({ enabled: true }) : 
  (config) => config;

const nextConfig = {
  reactStrictMode: true,
  // Explicitly use Pages Router
  useFileSystemPublicRoutes: true,
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
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // Enable React strict mode for better error detection
  experimental: {
    // Enable concurrent features
    concurrentFeatures: true,
    // Optimize server components
    serverComponents: false,
  },
  // Output standalone build for better deployment performance
  output: 'standalone',
};

module.exports = withBundleAnalyzer(nextConfig); 