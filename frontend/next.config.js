/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Explicitly use Pages Router
  useFileSystemPublicRoutes: true,
  // Specify which file extensions to use for Pages Router
  pageExtensions: ['tsx', 'ts', 'jsx', 'js']
};

module.exports = nextConfig; 