'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { listAnalyses, listConfigurations, getRuleVersions } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import type { AnalysisResponse, ConfigurationResponse } from '@/lib/types'

function scoreColor(score: number): string {
  if (score >= 80) return 'score-great'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-warn'
  if (score >= 20) return 'score-poor'
  return 'score-bad'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function configTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    dockerfile: 'Dockerfile',
    docker_compose: 'Docker Compose',
    github_actions: 'GitHub Actions',
    kubernetes: 'Kubernetes',
    terraform: 'Terraform',
  }
  return labels[t] ?? t
}

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([])
  const [configs, setConfigs] = useState<ConfigurationResponse[]>([])
  const [ruleVersions, setRuleVersions] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  useEffect(() => {
    if (!user) return
    Promise.all([listAnalyses(), listConfigurations(), getRuleVersions()])
      .then(([a, c, rv]) => {
        setAnalyses(a)
        setConfigs(c)
        setRuleVersions(rv)
      })
      .catch(() => setError('Failed to load dashboard data.'))
      .finally(() => setLoading(false))
  }, [user])

  if (authLoading || !user) return null

  const configMap = Object.fromEntries(configs.map((c) => [c.id, c]))
  const completed = analyses.filter((a) => a.status === 'completed' && a.overall_score !== null)
  const avgScore =
    completed.length > 0
      ? Math.round(completed.reduce((s, a) => s + (a.overall_score ?? 0), 0) / completed.length)
      : null
  const highRisk = completed.filter((a) => (a.overall_score ?? 100) < 60).length
  const recent = analyses.slice(0, 5)

  return (
    <main className="page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>Dashboard</h1>
          <p className="muted">Welcome back, {user.email}</p>
        </div>
        <Link href="/new" className="btn btn-primary">New Analysis</Link>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <p className="stat-label">Total Analyses</p>
          <p className="stat-value">{analyses.length}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">High Risk Configs</p>
          <p className="stat-value" style={{ color: highRisk > 0 ? '#f87171' : '#4ade80' }}>{highRisk}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Average Score</p>
          <p className={`stat-value ${avgScore !== null ? scoreColor(avgScore) : ''}`}>
            {avgScore !== null ? avgScore : '—'}
          </p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Configurations</p>
          <p className="stat-value">{configs.length}</p>
        </div>
      </div>

      <h2>Recent Analyses</h2>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error-msg">{error}</p>}

      {!loading && analyses.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: '#9ca3af', marginBottom: '1rem' }}>No analyses yet.</p>
          <Link href="/new" className="btn btn-primary">Run your first analysis</Link>
        </div>
      )}

      {!loading && recent.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Configuration</th>
                <th>Type</th>
                <th>Score</th>
                <th>Findings</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {recent.map((a) => {
                const cfg = configMap[a.configuration_id]
                const score = a.overall_score
                const isStale = cfg
                  ? a.rule_version !== null && ruleVersions[cfg.configuration_type] !== undefined
                    && a.rule_version !== ruleVersions[cfg.configuration_type]
                  : false
                return (
                  <tr key={a.id}>
                    <td style={{ color: '#f9fafb', fontWeight: 500 }}>
                      {cfg?.name ?? '—'}
                      {isStale && (
                        <span title="Rules have been updated since this analysis ran" style={{
                          marginLeft: '0.5rem',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          color: '#fbbf24',
                          background: '#1c1a0f',
                          border: '1px solid #713f12',
                          borderRadius: '9999px',
                          padding: '0.1rem 0.5rem',
                          verticalAlign: 'middle',
                        }}>
                          Rules updated
                        </span>
                      )}
                    </td>
                    <td className="muted">{cfg ? configTypeLabel(cfg.configuration_type) : '—'}</td>
                    <td>
                      {score !== null ? (
                        <span className={scoreColor(score)} style={{ fontWeight: 600 }}>{Math.round(score)}</span>
                      ) : (
                        <span className="muted">{a.status}</span>
                      )}
                    </td>
                    <td className="muted">{a.findings.length}</td>
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

      {!loading && analyses.length > 5 && (
        <div style={{ marginTop: '1rem', textAlign: 'right' }}>
          <Link href="/history" className="nav-link" style={{ color: '#818cf8' }}>
            View all analyses →
          </Link>
        </div>
      )}
    </main>
  )
}
