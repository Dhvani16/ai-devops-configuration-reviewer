'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { analyzeConfiguration, createConfiguration, getAnalysis } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import type { ConfigurationType } from '@/lib/types'

const CONFIG_TYPE_LABELS: Record<ConfigurationType, string> = {
  dockerfile: 'Dockerfile',
  docker_compose: 'Docker Compose',
  github_actions: 'GitHub Actions',
  kubernetes: 'Kubernetes',
  terraform: 'Terraform',
  helm: 'Helm Chart',
}

function detectType(filename: string): ConfigurationType {
  const base = filename.split('/').pop()?.toLowerCase() ?? filename.toLowerCase()
  if (base === 'dockerfile' || base.endsWith('.dockerfile')) return 'dockerfile'
  if (
    base.includes('docker-compose') ||
    base === 'compose.yml' ||
    base === 'compose.yaml'
  )
    return 'docker_compose'
  if (base.endsWith('.tf') || base.endsWith('.tfvars')) return 'terraform'
  if (
    base === 'values.yaml' ||
    base === 'values.yml' ||
    base === 'chart.yaml' ||
    base === 'chart.yml'
  )
    return 'helm'
  return 'kubernetes'
}

type ItemStatus = 'ready' | 'uploading' | 'analyzing' | 'polling' | 'done' | 'error'

interface BulkItem {
  localId: string
  fileName: string
  configType: ConfigurationType
  content: string
  status: ItemStatus
  analysisId?: string
  score?: number
  findingsCount?: number
  errorMsg?: string
}

function scoreColor(score: number): string {
  if (score >= 80) return '#4ade80'
  if (score >= 60) return '#facc15'
  if (score >= 40) return '#fb923c'
  return '#f87171'
}

let _localIdSeq = 0
function nextLocalId() { return String(++_localIdSeq) }

export default function BulkUploadPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const [items, setItems] = useState<BulkItem[]>([])
  const [running, setRunning] = useState(false)

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  function patchItem(localId: string, patch: Partial<BulkItem>) {
    setItems((prev) => prev.map((it) => (it.localId === localId ? { ...it, ...patch } : it)))
  }

  function handleFiles(files: FileList | null) {
    if (!files) return
    const readers = Array.from(files).map(
      (file) =>
        new Promise<BulkItem>((resolve) => {
          const reader = new FileReader()
          reader.onload = (ev) => {
            resolve({
              localId: nextLocalId(),
              fileName: file.name,
              configType: detectType(file.name),
              content: ev.target?.result as string,
              status: 'ready',
            })
          }
          reader.readAsText(file)
        })
    )
    Promise.all(readers).then((newItems) =>
      setItems((prev) => {
        const existing = new Set(prev.map((i) => i.fileName))
        return [...prev, ...newItems.filter((i) => !existing.has(i.fileName))]
      })
    )
  }

  function removeItem(localId: string) {
    setItems((prev) => prev.filter((i) => i.localId !== localId))
  }

  async function runItem(item: BulkItem) {
    try {
      patchItem(item.localId, { status: 'uploading' })
      const config = await createConfiguration({
        name: item.fileName,
        configuration_type: item.configType,
        original_content: item.content,
      })

      patchItem(item.localId, { status: 'analyzing' })
      const analysis = await analyzeConfiguration(config.id)
      patchItem(item.localId, { status: 'polling', analysisId: analysis.id })

      // Poll until complete
      let result = analysis
      while (result.status === 'pending' || result.status === 'running') {
        await new Promise((r) => setTimeout(r, 2000))
        result = await getAnalysis(result.id)
      }

      if (result.status === 'completed') {
        patchItem(item.localId, {
          status: 'done',
          score: result.overall_score ?? undefined,
          findingsCount: result.findings.length,
          analysisId: result.id,
        })
      } else {
        patchItem(item.localId, {
          status: 'error',
          errorMsg: result.error_message ?? 'Analysis failed.',
          analysisId: result.id,
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unexpected error.'
      patchItem(item.localId, { status: 'error', errorMsg: msg })
    }
  }

  async function handleRunAll() {
    const ready = items.filter((i) => i.status === 'ready')
    if (ready.length === 0) return
    setRunning(true)
    await Promise.allSettled(ready.map(runItem))
    setRunning(false)
  }

  if (authLoading || !user) return null

  const readyCount = items.filter((i) => i.status === 'ready').length
  const doneCount = items.filter((i) => i.status === 'done').length
  const inFlight = items.some((i) => ['uploading', 'analyzing', 'polling'].includes(i.status))

  return (
    <main className="page">
      <h1 style={{ fontSize: '1.75rem', marginBottom: '0.375rem' }}>Bulk Upload</h1>
      <p className="muted" style={{ marginBottom: '2rem' }}>
        Upload multiple configuration files and analyze them all at once.
      </p>

      {/* Drop zone */}
      <div
        style={{
          border: '2px dashed #374151',
          borderRadius: '0.75rem',
          padding: '2.5rem',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: '1.5rem',
          transition: 'border-color 0.15s',
        }}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files) }}
      >
        <p style={{ margin: 0, color: '#9ca3af', fontSize: '0.9375rem' }}>
          Click to select files, or drag and drop here
        </p>
        <p className="muted" style={{ margin: '0.375rem 0 0', fontSize: '0.8125rem' }}>
          Supports Dockerfile, docker-compose.yml, *.tf, values.yaml, Kubernetes / GitHub Actions YAML
        </p>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".yml,.yaml,Dockerfile,.dockerfile,.tf,.tfvars"
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {items.length > 0 && (
        <>
          <div className="table-wrap" style={{ marginBottom: '1.25rem' }}>
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.localId}>
                    <td style={{ color: '#f9fafb', fontWeight: 500, fontSize: '0.875rem' }}>
                      {item.fileName}
                    </td>
                    <td>
                      {item.status === 'ready' ? (
                        <select
                          value={item.configType}
                          onChange={(e) =>
                            patchItem(item.localId, {
                              configType: e.target.value as ConfigurationType,
                            })
                          }
                          className="input"
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.8125rem', width: 'auto' }}
                        >
                          {(Object.keys(CONFIG_TYPE_LABELS) as ConfigurationType[]).map((ct) => (
                            <option key={ct} value={ct}>{CONFIG_TYPE_LABELS[ct]}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="muted" style={{ fontSize: '0.8125rem' }}>
                          {CONFIG_TYPE_LABELS[item.configType]}
                        </span>
                      )}
                    </td>
                    <td>
                      <StatusBadge item={item} />
                    </td>
                    <td>
                      {item.status === 'done' && item.score !== undefined ? (
                        <span style={{ fontWeight: 700, color: scoreColor(item.score) }}>
                          {Math.round(item.score)}
                          <span className="muted" style={{ fontWeight: 400, fontSize: '0.75rem', marginLeft: '0.35rem' }}>
                            ({item.findingsCount} findings)
                          </span>
                        </span>
                      ) : item.status === 'error' ? (
                        <span style={{ color: '#f87171', fontSize: '0.8125rem' }}>{item.errorMsg}</span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {item.analysisId && (
                          <Link
                            href={`/analyses/${item.analysisId}`}
                            className="nav-link"
                            style={{ color: '#818cf8', fontSize: '0.8125rem' }}
                          >
                            View →
                          </Link>
                        )}
                        {item.status === 'ready' && (
                          <button
                            type="button"
                            onClick={() => removeItem(item.localId)}
                            style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: '0.875rem' }}
                            title="Remove"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleRunAll}
              disabled={readyCount === 0 || inFlight}
            >
              {inFlight ? (
                <>
                  <span className="spinner" style={{ width: '0.875rem', height: '0.875rem' }} />
                  Analyzing…
                </>
              ) : (
                `Analyze ${readyCount} file${readyCount !== 1 ? 's' : ''}`
              )}
            </button>
            {doneCount > 0 && (
              <span className="muted" style={{ fontSize: '0.875rem' }}>
                {doneCount} / {items.length} complete
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setItems([])}
              disabled={inFlight}
            >
              Clear all
            </button>
          </div>
        </>
      )}
    </main>
  )
}

function StatusBadge({ item }: { item: BulkItem }) {
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    fontSize: '0.75rem',
    fontWeight: 600,
    borderRadius: '9999px',
    padding: '0.15rem 0.6rem',
  }

  switch (item.status) {
    case 'ready':
      return <span style={{ ...style, background: '#1f2937', color: '#9ca3af' }}>Ready</span>
    case 'uploading':
      return (
        <span style={{ ...style, background: '#1c1a0f', color: '#fbbf24' }}>
          <span className="spinner" style={{ width: '0.6rem', height: '0.6rem' }} />
          Uploading
        </span>
      )
    case 'analyzing':
      return (
        <span style={{ ...style, background: '#1c1a0f', color: '#fbbf24' }}>
          <span className="spinner" style={{ width: '0.6rem', height: '0.6rem' }} />
          Analyzing
        </span>
      )
    case 'polling':
      return (
        <span style={{ ...style, background: '#1c1a0f', color: '#fbbf24' }}>
          <span className="spinner" style={{ width: '0.6rem', height: '0.6rem' }} />
          Waiting for AI
        </span>
      )
    case 'done':
      return <span style={{ ...style, background: '#052e16', color: '#4ade80' }}>Done</span>
    case 'error':
      return <span style={{ ...style, background: '#2d1414', color: '#f87171' }}>Error</span>
  }
}
