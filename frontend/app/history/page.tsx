'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { listAnalyses, listConfigurations } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import SeverityBadge from '@/components/SeverityBadge'
import type { AnalysisResponse, ConfigurationResponse } from '@/lib/types'

function scoreColor(score: number): string {
  if (score >= 80) return 'score-great'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-warn'
  if (score >= 20) return 'score-poor'
  return 'score-bad'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function configTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    dockerfile: 'Dockerfile',
    docker_compose: 'Docker Compose',
    github_actions: 'GitHub Actions',
  }
  return labels[t] ?? t
}

export default function HistoryPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([])
  const [configs, setConfigs] = useState<ConfigurationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  useEffect(() => {
    if (!user) return
    Promise.all([listAnalyses(), listConfigurations()])
      .then(([a, c]) => {
        setAnalyses(a)
        setConfigs(c)
      })
      .catch(() => setError('Failed to load history.'))
      .finally(() => setLoading(false))
  }, [user])

  if (authLoading || !user) return null

  const configMap = Object.fromEntries(configs.map((c) => [c.id, c]))

  return (
    <main className="page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem' }}>Analysis History</h1>
        <Link href="/new" className="btn btn-primary">New Analysis</Link>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error-msg">{error}</p>}

      {!loading && analyses.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: '#9ca3af', marginBottom: '1rem' }}>No analyses yet.</p>
          <Link href="/new" className="btn btn-primary">Run your first analysis</Link>
        </div>
      )}

      {!loading && analyses.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Configuration</th>
                <th>Type</th>
                <th>Score</th>
                <th>Findings</th>
                <th>Critical / High</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a) => {
                const cfg = configMap[a.configuration_id]
                const score = a.overall_score
                const critical = a.findings.filter((f) => f.severity === 'critical').length
                const high = a.findings.filter((f) => f.severity === 'high').length
                return (
                  <tr key={a.id}>
                    <td style={{ color: '#f9fafb', fontWeight: 500 }}>{cfg?.name ?? '—'}</td>
                    <td className="muted">{cfg ? configTypeLabel(cfg.configuration_type) : '—'}</td>
                    <td>
                      {score !== null ? (
                        <span className={scoreColor(score)} style={{ fontWeight: 600 }}>
                          {Math.round(score)}
                        </span>
                      ) : (
                        <span className="muted">{a.status}</span>
                      )}
                    </td>
                    <td className="muted">{a.findings.length}</td>
                    <td>
                      <span style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                        {critical > 0 && <SeverityBadge severity="critical" />}
                        {high > 0 && <SeverityBadge severity="high" />}
                        {critical === 0 && high === 0 && <span className="muted">—</span>}
                      </span>
                    </td>
                    <td className="muted">{formatDate(a.created_at)}</td>
                    <td>
                      <Link href={`/analyses/${a.id}`} className="nav-link" style={{ color: '#818cf8' }}>
                        View →
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
