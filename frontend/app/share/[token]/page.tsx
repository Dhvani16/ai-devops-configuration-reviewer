'use client'

import { useEffect, useState } from 'react'
import { use } from 'react'
import Link from 'next/link'
import { getSharedAnalysis } from '@/lib/api'
import SeverityBadge from '@/components/SeverityBadge'
import type { AnalysisResponse, FindingResponse, FindingSeverity } from '@/lib/types'

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
    kubernetes: 'Kubernetes',
    terraform: 'Terraform',
    helm: 'Helm Chart',
  }
  return labels[t] ?? t
}

function ReadOnlyFindingCard({ finding }: { finding: FindingResponse }) {
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
        <span className="muted" style={{ fontSize: '1rem', flexShrink: 0 }}>{open ? '▲' : '▼'}</span>
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
            <pre style={{
              margin: 0, background: '#0b1020', border: '1px solid #1f2937',
              borderRadius: '0.375rem', padding: '0.625rem 0.875rem',
              fontSize: '0.8125rem', color: '#94a3b8', overflowX: 'auto',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {finding.evidence}
            </pre>
          </div>
          <div>
            <p className="form-label" style={{ marginBottom: '0.25rem' }}>Recommendation</p>
            <p style={{ margin: 0, color: '#86efac', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {finding.recommendation}
            </p>
          </div>
          {finding.fix_suggestion && (
            <div>
              <p className="form-label" style={{ marginBottom: '0.25rem' }}>Suggested fix</p>
              <pre style={{
                margin: 0, background: '#021a0f', border: '1px solid #14532d',
                borderRadius: '0.375rem', padding: '0.625rem 0.875rem',
                fontSize: '0.8125rem', color: '#86efac', overflowX: 'auto',
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {finding.fix_suggestion}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SharedReportPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params)
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getSharedAnalysis(token)
      .then(setAnalysis)
      .catch(() => setError('Report not found or link has been revoked.'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <main className="page"><p className="muted">Loading…</p></main>
  if (error || !analysis) {
    return (
      <main className="page">
        <p className="error-msg">{error || 'Report not found.'}</p>
        <Link href="/" className="btn btn-secondary btn-sm" style={{ marginTop: '1rem' }}>
          Go to DevOps Reviewer →
        </Link>
      </main>
    )
  }

  const score = analysis.overall_score ?? 0
  const findingsBySeverity = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    findings: analysis.findings.filter((f) => f.severity === sev),
  })).filter((g) => g.findings.length > 0)

  const analyzedAt = new Date(analysis.created_at).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <main className="page">
      {/* Public banner */}
      <div style={{
        marginBottom: '1.5rem',
        padding: '0.625rem 1rem',
        background: '#0f172a',
        border: '1px solid #1f2937',
        borderRadius: '0.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.5rem',
      }}>
        <span className="muted" style={{ fontSize: '0.8125rem' }}>
          Shared read-only report · Analysed {analyzedAt}
        </span>
        <Link href="/" style={{ color: '#818cf8', fontSize: '0.8125rem' }}>
          DevOps Reviewer ↗
        </Link>
      </div>

      {/* Header card */}
      <div className="card" style={{ marginBottom: '2rem', display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center', minWidth: '7rem' }}>
          <p className={scoreColor(score)} style={{ fontSize: '3.5rem', fontWeight: 700, lineHeight: 1, margin: 0 }}>
            {Math.round(score)}
          </p>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Risk Score
          </p>
        </div>
        <div style={{ flex: 1, minWidth: '12rem' }}>
          <p style={{ margin: '0 0 0.25rem', fontWeight: 700, fontSize: '1.125rem', color: '#f9fafb' }}>
            Shared Configuration Report
          </p>
          <p className="muted" style={{ margin: 0 }}>
            {analysis.findings.length > 0
              ? configTypeLabel(String((analysis as unknown as { configuration_type?: string }).configuration_type ?? ''))
              : ''} {scoreLabel(score)}
          </p>
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

      {/* Findings */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span className="muted" style={{ fontSize: '0.875rem' }}>
          {analysis.findings.length} finding{analysis.findings.length !== 1 ? 's' : ''}
        </span>
      </div>

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
              <span className="muted" style={{ fontSize: '0.875rem' }}>
                {findings.length} finding{findings.length !== 1 ? 's' : ''}
              </span>
            </div>
            {findings.map((f) => <ReadOnlyFindingCard key={f.id} finding={f} />)}
          </section>
        ))
      )}

      <div style={{ marginTop: '2rem', textAlign: 'center' }}>
        <p className="muted" style={{ fontSize: '0.8125rem', marginBottom: '0.5rem' }}>
          Want to analyse your own configurations?
        </p>
        <Link href="/register" className="btn btn-primary">
          Try DevOps Reviewer →
        </Link>
      </div>
    </main>
  )
}
