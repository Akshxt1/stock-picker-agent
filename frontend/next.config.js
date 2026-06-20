/** @type {import('next').NextConfig} */
const nextConfig = {
  // API URL — set NEXT_PUBLIC_API_URL in Vercel env vars
  // e.g. https://your-app.up.railway.app
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
}

module.exports = nextConfig
