/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // One worker keeps generated segment directories reliable on synced Windows folders.
  experimental: { cpus: 1 },
};
export default nextConfig;
