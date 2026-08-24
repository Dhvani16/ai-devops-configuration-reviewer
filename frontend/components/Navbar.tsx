'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'

export default function Navbar() {
  const { user, signOut } = useAuth()
  const router = useRouter()

  function handleSignOut() {
    signOut()
    router.push('/')
  }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="navbar-brand">
          DevOps Reviewer
        </Link>
        <div className="navbar-links">
          {user ? (
            <>
              <Link href="/dashboard" className="nav-link">Dashboard</Link>
              <Link href="/new" className="nav-link">New Analysis</Link>
              <Link href="/history" className="nav-link">History</Link>
              <button onClick={handleSignOut} className="nav-link nav-btn">
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="nav-link">Sign in</Link>
              <Link href="/register" className="btn btn-primary" style={{ padding: '0.4rem 0.875rem', fontSize: '0.875rem' }}>
                Get started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
