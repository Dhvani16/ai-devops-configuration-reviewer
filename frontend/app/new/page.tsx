'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError, analyzeConfiguration, createConfiguration } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import type { ConfigurationType } from '@/lib/types'

const CONFIG_TYPES: { value: ConfigurationType; label: string; placeholder: string }[] = [
  {
    value: 'dockerfile',
    label: 'Dockerfile',
    placeholder: 'FROM python:3.12\nRUN apt-get update && apt-get install -y ...\n...',
  },
  {
    value: 'docker_compose',
    label: 'Docker Compose',
    placeholder: 'version: "3"\nservices:\n  app:\n    image: nginx\n    ...',
  },
  {
    value: 'github_actions',
    label: 'GitHub Actions',
    placeholder: 'name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      ...',
  },
]

export default function NewAnalysisPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)

  const [name, setName] = useState('')
  const [configType, setConfigType] = useState<ConfigurationType>('dockerfile')
  const [content, setContent] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<'idle' | 'creating' | 'analyzing'>('idle')

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setContent(ev.target?.result as string)
    reader.readAsText(file)
    if (!name) setName(file.name)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) {
      setError('Please paste or upload a configuration file.')
      return
    }
    setError('')
    setLoading(true)
    setStep('creating')

    try {
      const config = await createConfiguration({
        name: name.trim() || 'Untitled',
        configuration_type: configType,
        original_content: content,
      })
      setStep('analyzing')
      const analysis = await analyzeConfiguration(config.id)
      router.push(`/analyses/${analysis.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Analysis failed. Please try again.')
      setLoading(false)
      setStep('idle')
    }
  }

  if (authLoading || !user) return null

  const selectedType = CONFIG_TYPES.find((t) => t.value === configType)!

  return (
    <main className="page">
      <div style={{ maxWidth: '48rem' }}>
        <h1 style={{ fontSize: '1.75rem', marginBottom: '0.375rem' }}>New Analysis</h1>
        <p className="muted" style={{ marginBottom: '2rem' }}>
          Paste a configuration file to run static and AI analysis.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.375rem' }}>
          {/* Type selector */}
          <div className="form-group">
            <label className="form-label">Configuration type</label>
            <div style={{ display: 'flex', gap: '0.625rem' }}>
              {CONFIG_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setConfigType(t.value)}
                  className="btn btn-secondary"
                  style={{
                    borderColor: configType === t.value ? '#4f46e5' : '#374151',
                    color: configType === t.value ? '#a5b4fc' : '#9ca3af',
                    backgroundColor: configType === t.value ? '#1e1b4b' : 'transparent',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div className="form-group">
            <label className="form-label" htmlFor="name">Name (optional)</label>
            <input
              id="name"
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. production-dockerfile"
              maxLength={255}
            />
          </div>

          {/* Content */}
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
              <label className="form-label" htmlFor="content">Configuration content</label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => fileRef.current?.click()}
              >
                Upload file
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".yml,.yaml,Dockerfile,.dockerfile"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
            </div>
            <textarea
              id="content"
              className="textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={selectedType.placeholder}
              style={{ minHeight: '16rem' }}
              spellCheck={false}
            />
          </div>

          {error && <p className="error-msg">{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ alignSelf: 'flex-start' }}>
            {loading ? (
              <>
                <span className="spinner" style={{ width: '0.875rem', height: '0.875rem' }} />
                {step === 'creating' ? 'Saving configuration…' : 'Running analysis…'}
              </>
            ) : (
              'Analyze configuration'
            )}
          </button>
        </form>
      </div>
    </main>
  )
}
