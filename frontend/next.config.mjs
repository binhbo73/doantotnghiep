/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Configure proxy for Next.js 16
  skipProxyUrlNormalize: true,
}

export default nextConfig
