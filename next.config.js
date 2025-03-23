/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Improve static asset caching
  async headers() {
    return [
      {
        // Apply these headers to all routes in the application
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          }
        ],
      },
      {
        // Cache static assets with a long max-age
        source: '/:path*.(jpg|jpeg|png|gif|webp|svg|woff|woff2|ttf|otf|eot|ico|css|js)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          }
        ],
      },
    ]
  },
  
  // Optimize image handling
  images: {
    domains: [
      // Add your domains here, e.g., Supabase Storage domain
      'localhost',
    ],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // Configure webpack to reduce bundle size
  webpack(config) {
    // Grab the existing rule that handles SVG imports
    const fileLoaderRule = config.module.rules.find(
      (rule) => rule.test && rule.test.test('.svg')
    );

    config.module.rules.push(
      // Convert SVGs to React components for better performance
      {
        test: /\.svg$/,
        issuer: /\.[jt]sx?$/,
        use: ['@svgr/webpack'],
      }
    );
    
    return config;
  },
  
  // Modern CSS optimization
  experimental: {
    // Only keep supported experimental features
    optimizeCss: true
  }
}

module.exports = nextConfig 