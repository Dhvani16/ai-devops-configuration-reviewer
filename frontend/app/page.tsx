import Link from 'next/link'

const features = [
  {
    title: 'Static Analysis',
    desc: 'Deterministic rule engine catches known misconfigurations instantly — no AI required.',
  },
  {
    title: 'AI Reasoning',
    desc: 'Schema-validated LLM analysis explains context, prioritises findings, and suggests fixes.',
  },
  {
    title: 'Risk Scoring',
    desc: 'Deterministic scoring combines finding severity into an actionable 0–100 risk score.',
  },
  {
    title: 'Full Audit Trail',
    desc: 'Every analysis is persisted so you can compare configurations over time.',
  },
]

const supportedTypes = ['Dockerfile', 'Docker Compose', 'GitHub Actions']

export default function HomePage() {
  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">AI DevOps Configuration Reviewer</p>
        <h1>Find configuration risk before it reaches production.</h1>
        <p className="intro">
          Combine deterministic checks and schema-validated AI reasoning to review
          Dockerfiles, Compose files, and GitHub Actions workflows in seconds.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link href="/register" className="btn btn-primary">Get started free</Link>
          <Link href="/login" className="btn btn-secondary">Sign in</Link>
        </div>
      </section>

      <section style={{ marginTop: '4rem' }}>
        <h2>How it works</h2>
        <div className="feature-grid">
          {features.map((f) => (
            <div key={f.title} className="feature-card">
              <p className="feature-title">{f.title}</p>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: '3rem' }}>
        <h2>Supported configuration types</h2>
        <ul className="type-pills">
          {supportedTypes.map((t) => <li key={t}>{t}</li>)}
        </ul>
      </section>
    </main>
  )
}
