import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/components/AuthProvider'
import Navbar from '@/components/Navbar'

export const metadata: Metadata = {
  title: 'AI DevOps Configuration Reviewer',
  description: 'Find risks in DevOps configuration before production.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Navbar />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
