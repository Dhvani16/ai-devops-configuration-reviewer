'use client'

import { useEffect, useState } from 'react'
import { use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { getAnalysis, listConfigurations } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import SeverityBadge from '@/components/SeverityBadge'
import type { AnalysisResponse, ConfigurationResponse, FindingResponse, FindingSeverity } from '@/lib/types'

const SEVERITY_ORDER: FindingSeverity[] = ['critical', 'high', 'medium', 'low']

function scoreColor(score: number): string {
  if (score >= 80) return 'score-great'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-warn'
  if (score >= 20) return 'score-poor'
  return 'score-bad'
}

function scoreLabel(score: number): string {
  if (score >= 80) return 'Low Risk'
  if (score >= 60) return 'Moderate Risk'
  if (score >= 40) return 'High Risk'
  return 'Critical Risk'
}

function configTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    dockerfile: 'Dockerfile',
    docker_compose: 'Docker Compose',
    github_actions: 'GitHub Actions',
  }
  return labels[t] ?? t
}

function FindingCard({ finding }: { finding: FindingResponse }) {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="card"
      style={{ padding: '1rem', marginBottom: '0.625rem', cursor: 'pointer' }}
      onClick={() => setOpen(!open)}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
        <SeverityBadge severity={finding.severity} />
        <span
          className={`source-tag source-${finding.source}`}
          style={{ marginTop: '0.05rem' }}
        >
          {finding.source === 'ai' ? 'AI' : 'Static'}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9375rem', color: '#f9fafb' }}>
            {finding.title}
          </p>
          {finding.line_number && (
            <p className="muted" style={{ margin: '0.125rem 0 0', fontSize: '0.75rem' }}>
              Line {finding.line_number}
            </p>
          )}
        </div>
        <span className="muted" style={{ fontSize: '1rem', flexShrink: 0 }}>
          {open ? '▲' : '▼'}
        </span>
      </div>

      {open && (
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          <div>
            <p className="form-label" style={{ marginBottom: '0.25rem' }}>Description</p>
            <p style={{ margin: 0, color: '#d1d5db', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {finding.description}
            </p>
          </div>
          <div>
            <p className="form-label" style={{ marginBottom: '0.25rem' }}>Evidence</p>
            <pre
              style={{
                margin: 0,
                background: '#0b1020',
                border: '1px solid #1f2937',
                borderRadius: '0.375rem',
                padding: '0.625rem 0.875rem',
                fontSize: '0.8125rem',
                color: '#94a3b8',
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {finding.evidence}
            </pre>
          </div>
          <div>
            <p className="form-label" style={{ marginBottom: '0.25rem' }}>Recommendation</p>
            <p style={{ margin: 0, color: '#86efac', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {finding.recommendation}
            </p>
          </div>
          {finding.confidence !== null && (
            <p className="muted" style={{ fontSize: '0.75rem', margin: 0 }}>
              AI confidence: {Math.round(finding.confidence * 100)}%
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function AnalysisResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [config, setConfig] = useState<ConfigurationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  useEffect(() => {
    if (!user) return
    Promise.all([getAnalysis(id), listConfigurations()])
      .then(([a, configs]) => {
        setAnalysis(a)
        setConfig(configs.find((c) => c.id === a.configuration_id) ?? null)
      })
      .catch(() => setError('Failed to load analysis.'))
      .finally(() => setLoading(false))
  }, [user, id])

  if (authLoading || !user) return null
  if (loading) return <main className="page"><p className="muted">Loading…</p></main>
  if (error) return <main className="page"><p className="error-msg">{error}</p></main>
  if (!analysis) return null

  const score = analysis.overall_score ?? 0
  const findingsBySeverity = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    findings: analysis.findings.filter((f) => f.severity === sev),
  })).filter((g) => g.findings.length > 0)

  const aiCount = analysis.findings.filter((f) => f.source === 'ai').length
  const staticCount = analysis.findings.filter((f) => f.source === 'deterministic').length

  return (
    <main className="page">
      {/* Breadcrumb */}
      <p className="muted" style={{ marginBottom: '1.5rem', fontSize: '0.875rem' }}>
        <Link href="/history" style={{ color: '#818cf8' }}>History</Link>
        {' / '}
        <span>{config?.name ?? 'Analysis'}</span>
      </p>

      {/* Header card */}
      <div className="card" style={{ marginBottom: '2rem', display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center', minWidth: '7rem' }}>
          <p
            className={scoreColor(score)}
            style={{ fontSize: '3.5rem', fontWeight: 700, lineHeight: 1, margin: 0 }}
          >
            {Math.round(score)}
          </p>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Risk Score
          </p>
        </div>
        <div style={{ flex: 1, minWidth: '12rem' }}>
          <p style={{ margin: '0 0 0.25rem', fontWeight: 700, fontSize: '1.125rem', color: '#f9fafb' }}>
            {config?.name ?? 'Configuration'}
          </p>
          <p className="muted" style={{ margin: 0 }}>
            {config ? configTypeLabel(config.configuration_type) : ''} · {scoreLabel(score)}
          </p>
          {analysis.error_message && (
            <p style={{ margin: '0.5rem 0 0', color: '#fbbf24', fontSize: '0.8125rem' }}>
              ⚠ {analysis.error_message}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'flex-end' }}>
          {(['critical', 'high', 'medium', 'low'] as FindingSeverity[]).map((sev) => {
            const count = analysis.findings.filter((f) => f.severity === sev).length
            return count > 0 ? (
              <span key={sev} style={{ display: 'flex', gap: '0.375rem', alignItems: 'center' }}>
                <SeverityBadge severity={sev} />
                <span className="muted" style={{ fontSize: '0.8125rem' }}>{count}</span>
              </span>
            ) : null
          })}
        </div>
      </div>

      {/* Source summary */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <span>
          <span className="source-tag source-deterministic">{staticCount} Static</span>
        </span>
        <span>
          <span className="source-tag source-ai">{aiCount} AI</span>
        </span>
        <span className="muted" style={{ fontSize: '0.8125rem', alignSelf: 'center' }}>
          {analysis.findings.length} total finding{analysis.findings.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Findings */}
      {analysis.findings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem' }}>
          <p style={{ color: '#4ade80', fontWeight: 600, fontSize: '1.125rem', margin: 0 }}>
            No findings — configuration looks clean!
          </p>
        </div>
      ) : (
        findingsBySeverity.map(({ severity, findings }) => (
          <section key={severity} style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <SeverityBadge severity={severity} />
              <span className="muted" style={{ fontSize: '0.875rem' }}>{findings.length} finding{findings.length !== 1 ? 's' : ''}</span>
            </div>
            {findings.map((f) => <FindingCard key={f.id} finding={f} />)}
          </section>
        ))
      )}

      <div style={{ marginTop: '2rem' }}>
        <Link href="/new" className="btn btn-secondary btn-sm">Analyze another →</Link>
      </div>
    </main>
  )
}
