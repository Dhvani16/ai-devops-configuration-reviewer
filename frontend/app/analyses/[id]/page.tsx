'use client'

import { useEffect, useRef, useState } from 'react'
import { use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ApiError, analyzeConfiguration, downloadSarif, explainScore, getAnalysis, getChatHistory, getConfiguration, getConfigurationTrend, sendChatMessage } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import SeverityBadge from '@/components/SeverityBadge'
import type { AnalysisResponse, ChatMessage, ConfigurationResponse, FindingCategory, FindingResponse, FindingSeverity, TrendPoint } from '@/lib/types'

const SEVERITY_ORDER: FindingSeverity[] = ['critical', 'high', 'medium', 'low']
const CATEGORIES: { value: FindingCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'security', label: 'Security' },
  { value: 'reliability', label: 'Reliability' },
  { value: 'performance', label: 'Performance' },
  { value: 'maintainability', label: 'Maintainability' },
]

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

function ScoreTrendChart({ points }: { points: TrendPoint[] }) {
  if (points.length < 2) {
    return (
      <p className="muted" style={{ fontSize: '0.875rem', margin: 0 }}>
        Not enough data yet — run at least 2 analyses to see the trend.
      </p>
    )
  }

  const W = 480
  const H = 100
  const PAD = { top: 12, right: 16, bottom: 28, left: 32 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom

  const minScore = Math.max(0, Math.min(...points.map((p) => p.overall_score)) - 5)
  const maxScore = Math.min(100, Math.max(...points.map((p) => p.overall_score)) + 5)

  const xScale = (i: number) => PAD.left + (i / (points.length - 1)) * chartW
  const yScale = (s: number) => PAD.top + chartH - ((s - minScore) / (maxScore - minScore)) * chartH

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i).toFixed(1)} ${yScale(p.overall_score).toFixed(1)}`)
    .join(' ')

  function dotColor(score: number): string {
    if (score >= 80) return '#4ade80'
    if (score >= 60) return '#facc15'
    if (score >= 40) return '#fb923c'
    return '#f87171'
  }

  function fmtDate(iso: string): string {
    const d = new Date(iso)
    return `${d.getDate()} ${d.toLocaleString('en', { month: 'short' })}`
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: `${W / 2}px`, display: 'block' }}>
        {/* Y-axis grid lines */}
        {[0, 50, 100].map((v) => {
          if (v < minScore || v > maxScore) return null
          const y = yScale(v)
          return (
            <g key={v}>
              <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y} stroke="#1f2937" strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 4} fill="#6b7280" fontSize={9} textAnchor="end">{v}</text>
            </g>
          )
        })}
        {/* Trend line */}
        <path d={pathD} fill="none" stroke="#4f46e5" strokeWidth={2} strokeLinejoin="round" />
        {/* Data points */}
        {points.map((p, i) => (
          <g key={p.analysis_id}>
            <circle
              cx={xScale(i)}
              cy={yScale(p.overall_score)}
              r={4}
              fill={dotColor(p.overall_score)}
              stroke="#0f172a"
              strokeWidth={1.5}
            >
              <title>{`${fmtDate(p.created_at)}: score ${Math.round(p.overall_score)}, ${p.total} findings`}</title>
            </circle>
            <text
              x={xScale(i)}
              y={yScale(p.overall_score) - 7}
              fill={dotColor(p.overall_score)}
              fontSize={8}
              textAnchor="middle"
              fontWeight={600}
            >
              {Math.round(p.overall_score)}
            </text>
            {/* X-axis date label */}
            <text
              x={xScale(i)}
              y={H - 4}
              fill="#6b7280"
              fontSize={8}
              textAnchor="middle"
            >
              {fmtDate(p.created_at)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

function FindingCard({ finding }: { finding: FindingResponse }) {
  const [open, setOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function openChat() {
    setChatOpen(true)
    if (!historyLoaded) {
      try {
        const history = await getChatHistory(finding.id)
        setMessages(history)
      } catch {
        // ignore — empty history is fine
      }
      setHistoryLoaded(true)
    }
  }

  function toggleChat(e: React.MouseEvent) {
    e.stopPropagation()
    if (!chatOpen) {
      openChat()
    } else {
      setChatOpen(false)
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    e.stopPropagation()
    const text = chatInput.trim()
    if (!text || chatLoading) return
    setChatInput('')
    setChatError('')
    setChatLoading(true)
    setMessages((prev) => [...prev, { id: 'tmp', finding_id: finding.id, role: 'user', content: text, created_at: new Date().toISOString() }])
    try {
      const reply = await sendChatMessage(finding.id, text)
      setMessages((prev) => [...prev.filter((m) => m.id !== 'tmp'), { id: 'usr-' + reply.id, finding_id: finding.id, role: 'user', content: text, created_at: reply.created_at }, reply])
    } catch (err) {
      setChatError(err instanceof ApiError ? err.message : 'Failed to send message.')
      setMessages((prev) => prev.filter((m) => m.id !== 'tmp'))
    } finally {
      setChatLoading(false)
    }
  }

  useEffect(() => {
    if (chatOpen) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, chatOpen])

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
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={toggleChat}
          style={{ flexShrink: 0, fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
        >
          {chatOpen ? 'Close chat' : '💬 Ask AI'}
        </button>
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
          {finding.fix_suggestion && (
            <div>
              <p className="form-label" style={{ marginBottom: '0.25rem' }}>Suggested fix</p>
              <pre
                style={{
                  margin: 0,
                  background: '#021a0f',
                  border: '1px solid #14532d',
                  borderRadius: '0.375rem',
                  padding: '0.625rem 0.875rem',
                  fontSize: '0.8125rem',
                  color: '#86efac',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {finding.fix_suggestion}
              </pre>
            </div>
          )}
          {finding.confidence !== null && (
            <p className="muted" style={{ fontSize: '0.75rem', margin: 0 }}>
              AI confidence: {Math.round(finding.confidence * 100)}%
            </p>
          )}
        </div>
      )}

      {chatOpen && (
        <div
          style={{ marginTop: '1rem', borderTop: '1px solid #1f2937', paddingTop: '1rem' }}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="form-label" style={{ marginBottom: '0.625rem' }}>Remediation chat</p>
          <div
            style={{
              background: '#0b1020',
              border: '1px solid #1f2937',
              borderRadius: '0.5rem',
              padding: '0.75rem',
              maxHeight: '16rem',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.625rem',
              marginBottom: '0.625rem',
            }}
          >
            {messages.length === 0 && (
              <p className="muted" style={{ fontSize: '0.8125rem', textAlign: 'center', margin: '1rem 0' }}>
                Ask a question about this finding — e.g. "Why is this dangerous?" or "Show me the fix."
              </p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  background: msg.role === 'user' ? '#1e1b4b' : '#111827',
                  border: `1px solid ${msg.role === 'user' ? '#3730a3' : '#374151'}`,
                  borderRadius: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.8125rem',
                  color: msg.role === 'user' ? '#a5b4fc' : '#d1d5db',
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {msg.content}
              </div>
            ))}
            {chatLoading && (
              <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span className="spinner" style={{ width: '0.75rem', height: '0.75rem' }} />
                <span className="muted" style={{ fontSize: '0.75rem' }}>Thinking…</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          {chatError && <p className="error-msg" style={{ fontSize: '0.75rem', margin: '0 0 0.5rem' }}>{chatError}</p>}
          <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              className="input"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about this finding…"
              disabled={chatLoading}
              style={{ flex: 1, fontSize: '0.875rem', padding: '0.5rem 0.75rem' }}
            />
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={chatLoading || !chatInput.trim()}
            >
              Send
            </button>
          </form>
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
  const [activeCategory, setActiveCategory] = useState<FindingCategory | 'all'>('all')
  const [minConfidence, setMinConfidence] = useState(0)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [reanalyzeError, setReanalyzeError] = useState('')
  const [sarifDownloading, setSarifDownloading] = useState(false)
  const [scoreExplanation, setScoreExplanation] = useState('')
  const [scoreExplaining, setScoreExplaining] = useState(false)
  const [trend, setTrend] = useState<TrendPoint[] | null>(null)
  const [trendOpen, setTrendOpen] = useState(false)
  const [trendLoading, setTrendLoading] = useState(false)

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  useEffect(() => {
    if (!user) return
    getAnalysis(id)
      .then((a) => {
        setAnalysis(a)
        return getConfiguration(a.configuration_id)
      })
      .then(setConfig)
      .catch(() => setError('Failed to load analysis.'))
      .finally(() => setLoading(false))
  }, [user, id])

  // Poll every 2 s while the analysis is pending/running
  useEffect(() => {
    const status = analysis?.status
    if (!status || (status !== 'pending' && status !== 'running')) return
    const timer = setInterval(() => {
      getAnalysis(id).then((a) => {
        setAnalysis(a)
        if (a.status !== 'pending' && a.status !== 'running') clearInterval(timer)
      }).catch(() => clearInterval(timer))
    }, 2000)
    return () => clearInterval(timer)
  }, [analysis?.status, id])

  async function handleReanalyze() {
    if (!analysis) return
    setReanalyzing(true)
    setReanalyzeError('')
    try {
      const newAnalysis = await analyzeConfiguration(analysis.configuration_id)
      router.push(`/analyses/${newAnalysis.id}`)
    } catch (err) {
      setReanalyzeError(err instanceof ApiError ? err.message : 'Re-analysis failed.')
      setReanalyzing(false)
    }
  }

  async function handleExplainScore() {
    setScoreExplaining(true)
    setScoreExplanation('')
    try {
      const result = await explainScore(id)
      setScoreExplanation(result.explanation)
    } catch {
      setScoreExplanation('Could not generate explanation.')
    } finally {
      setScoreExplaining(false)
    }
  }

  async function handleToggleTrend() {
    if (trendOpen) { setTrendOpen(false); return }
    setTrendOpen(true)
    if (trend !== null) return
    setTrendLoading(true)
    try {
      const points = await getConfigurationTrend(analysis!.configuration_id)
      setTrend(points)
    } catch {
      setTrend([])
    } finally {
      setTrendLoading(false)
    }
  }

  async function handleDownloadSarif() {
    setSarifDownloading(true)
    try {
      await downloadSarif(id)
    } finally {
      setSarifDownloading(false)
    }
  }

  if (authLoading || !user) return null
  if (loading) return <main className="page"><p className="muted">Loading…</p></main>
  if (error) return <main className="page"><p className="error-msg">{error}</p></main>
  if (!analysis) return null

  const isPending = analysis.status === 'pending' || analysis.status === 'running'
  const score = analysis.overall_score ?? 0

  const visibleFindings = analysis.findings
    .filter((f) => activeCategory === 'all' || f.category === activeCategory)
    .filter((f) => f.confidence === null || f.confidence * 100 >= minConfidence)

  const findingsBySeverity = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    findings: visibleFindings.filter((f) => f.severity === sev),
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

      {/* Pending / running banner */}
      {isPending && (
        <div style={{
          marginBottom: '1.5rem',
          padding: '0.875rem 1.25rem',
          background: '#1c1a0f',
          border: '1px solid #713f12',
          borderRadius: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <span className="spinner" style={{ width: '1rem', height: '1rem', flexShrink: 0 }} />
          <span style={{ color: '#fbbf24', fontSize: '0.9rem' }}>
            AI analysis is running — static findings shown below. Results will update automatically.
          </span>
        </div>
      )}

      {/* Header card */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
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
            {!isPending && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleExplainScore}
                disabled={scoreExplaining}
                style={{ marginTop: '0.5rem', fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
              >
                {scoreExplaining ? '…' : 'Explain'}
              </button>
            )}
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
        {(scoreExplaining || scoreExplanation) && (
          <div style={{
            marginTop: '1rem',
            paddingTop: '1rem',
            borderTop: '1px solid #1f2937',
          }}>
            {scoreExplaining ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="spinner" style={{ width: '0.875rem', height: '0.875rem', flexShrink: 0 }} />
                <span className="muted" style={{ fontSize: '0.875rem' }}>Generating explanation…</span>
              </div>
            ) : (
              <p style={{ margin: 0, color: '#d1d5db', fontSize: '0.875rem', lineHeight: 1.7 }}>
                {scoreExplanation}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Source summary + Re-analyze */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <span><span className="source-tag source-deterministic">{staticCount} Static</span></span>
        <span><span className="source-tag source-ai">{aiCount} AI</span></span>
        <span className="muted" style={{ fontSize: '0.8125rem', alignSelf: 'center' }}>
          {analysis.findings.length} total finding{analysis.findings.length !== 1 ? 's' : ''}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleDownloadSarif}
            disabled={sarifDownloading || isPending}
            title="Download SARIF 2.1 (GitHub Code Scanning compatible)"
          >
            {sarifDownloading ? '…' : '↓ SARIF'}
          </button>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleReanalyze}
              disabled={reanalyzing}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              {reanalyzing ? (
                <><span className="spinner" style={{ width: '0.75rem', height: '0.75rem' }} /> Re-analyzing…</>
              ) : (
                '↻ Re-analyze'
              )}
            </button>
            {reanalyzeError && (
              <p className="error-msg" style={{ margin: 0, fontSize: '0.75rem' }}>{reanalyzeError}</p>
            )}
          </div>
        </div>
      </div>

      {/* Category filter tabs */}
      <div style={{ display: 'flex', gap: '0.375rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {CATEGORIES.map(({ value, label }) => {
          const count = value === 'all'
            ? analysis.findings.length
            : analysis.findings.filter((f) => f.category === value).length
          const active = activeCategory === value
          return (
            <button
              key={value}
              type="button"
              onClick={() => setActiveCategory(value)}
              className="btn btn-secondary btn-sm"
              style={{
                borderColor: active ? '#4f46e5' : '#374151',
                color: active ? '#a5b4fc' : '#9ca3af',
                backgroundColor: active ? '#1e1b4b' : 'transparent',
              }}
            >
              {label}
              <span style={{
                marginLeft: '0.375rem',
                background: active ? '#4f46e5' : '#374151',
                color: '#fff',
                borderRadius: '9999px',
                padding: '0 0.4rem',
                fontSize: '0.7rem',
                fontWeight: 600,
              }}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* AI confidence threshold slider */}
      {aiCount > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '1.5rem',
          padding: '0.625rem 1rem',
          background: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '0.5rem',
        }}>
          <span className="muted" style={{ fontSize: '0.8125rem', flexShrink: 0 }}>
            Min AI confidence
          </span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            style={{ flex: 1, accentColor: '#4f46e5', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.8125rem', color: '#a5b4fc', fontWeight: 600, minWidth: '2.5rem', textAlign: 'right' }}>
            {minConfidence}%
          </span>
        </div>
      )}

      {/* Findings */}
      {visibleFindings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem' }}>
          <p style={{ color: '#4ade80', fontWeight: 600, fontSize: '1.125rem', margin: 0 }}>
            {activeCategory === 'all'
              ? 'No findings — configuration looks clean!'
              : `No ${activeCategory} findings.`}
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
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleToggleTrend}
          disabled={trendLoading}
          style={{ marginBottom: '0.75rem' }}
        >
          {trendLoading ? '…' : trendOpen ? '▲ Hide trend' : '↗ Score trend'}
        </button>
        {trendOpen && (
          <div className="card" style={{ padding: '1rem' }}>
            <p style={{ margin: '0 0 0.75rem', fontWeight: 600, color: '#f9fafb', fontSize: '0.9375rem' }}>
              Score over time — {config?.name}
            </p>
            {trendLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="spinner" style={{ width: '0.875rem', height: '0.875rem' }} />
                <span className="muted" style={{ fontSize: '0.875rem' }}>Loading…</span>
              </div>
            ) : (
              <ScoreTrendChart points={trend ?? []} />
            )}
          </div>
        )}
        <div style={{ marginTop: '0.75rem' }}>
          <Link href="/new" className="btn btn-secondary btn-sm">Analyze another →</Link>
        </div>
      </div>
    </main>
  )
}
