import type React from 'react'
import type { Metadata } from 'next'

import { Analytics } from '@vercel/analytics/next'
import './globals.css'

import { AuthProvider } from '@/lib/auth/auth-context'
import { Toaster } from '@/components/ui/toaster'

export const metadata: Metadata = {
  title: 'finio - Stock Research Platform',
  description:
    'finio is a stock research and analysis platform. Search stocks by ISIN, WKN, or symbol and build your watchlist.',
  icons: {
    icon: [
      {
        url: '/finio_logo_blau.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/finio_logo_blau.svg',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://rsms.me/" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        {/* Umami Analytics */}
        <script
          defer
          src="https://analytics.finio.cloud/script.js"
          data-website-id="32bab9a3-8459-40c9-be17-dac01ffcf3e5"
        />
      </head>
      <body className="font-sans antialiased">
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
        <Analytics />
      </body>
    </html>
  )
}
