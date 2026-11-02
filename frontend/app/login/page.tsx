'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ApiError, login } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await login(email, password)
      await signIn(access_token)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign in failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <div style={{ maxWidth: '24rem', margin: '3rem auto' }}>
        <h1 style={{ fontSize: '1.75rem', marginBottom: '0.375rem' }}>Sign in</h1>
        <p className="muted" style={{ marginBottom: '2rem' }}>
          New here?{' '}
          <Link href="/register" style={{ color: '#818cf8' }}>
            Create an account
          </Link>
        </p>

        <form
          onSubmit={handleSubmit}
          className="card"
          style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}
        >
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && <p className="error-msg">{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" style={{ width: '0.875rem', height: '0.875rem' }} />
                Signing in…
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>
      </div>
    </main>
  )
}
