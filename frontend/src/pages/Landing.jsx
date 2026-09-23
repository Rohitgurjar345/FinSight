import React from 'react'
import { Link } from 'react-router-dom'
import GlassPanel from '../components/GlassPanel.jsx'

const FEATURES = [
  {
    title: 'Categorized automatically',
    body: 'Every transaction is matched to a category the moment you upload — food, travel, utilities, and more — with a confidence score attached, not a silent guess.',
  },
  {
    title: 'A health score you can audit',
    body: 'Four weighted factors, each shown against a real population percentile. No black box — you can see exactly why the number is what it is.',
  },
  {
    title: 'Ask it questions directly',
    body: 'How much did I spend on food last month? What is my top category? Ask in plain language and get an answer computed from your own data.',
  },
]

export default function Landing() {
  return (
    <main>
      <section className="container" style={{ padding: '4rem 1.5rem 2rem', display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '3rem', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-3xl)', maxWidth: '14ch' }}>
            Understand exactly where your money goes.
          </h1>
          <p style={{ marginTop: '1.25rem', fontSize: 'var(--text-lg)', color: 'var(--muted)', maxWidth: '48ch' }}>
            Upload a bank statement. See it categorized, scored, and explained —
            no spreadsheets, no manual tagging.
          </p>
          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
            <Link to="/dashboard" className="btn btn-primary">Open the dashboard</Link>
          </div>
        </div>

        <GlassPanel cornerRadius={22} style={{ padding: '1.75rem' }}>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)', marginBottom: '1rem' }}>
            A preview of what the dashboard shows after upload
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ color: 'var(--muted)', fontSize: 'var(--text-sm)' }}>Health score</span>
            <span className="numeric" style={{ fontSize: 'var(--text-2xl)', color: 'var(--signal)' }}>68.9</span>
          </div>
          <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {[
              ['Groceries', 42],
              ['Utilities', 18],
              ['Transport', 12],
              ['Entertainment', 8],
            ].map(([label, pct]) => (
              <div key={label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                  <span>{label}</span>
                  <span className="numeric">{pct}%</span>
                </div>
                <div style={{ height: 6, borderRadius: 4, background: 'var(--surface-raised)' }}>
                  <div style={{ height: '100%', width: `${pct * 2}%`, borderRadius: 4, background: 'var(--signal)' }} />
                </div>
              </div>
            ))}
          </div>
        </GlassPanel>
      </section>

      <section className="container" style={{ padding: '3rem 1.5rem', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem' }}>
        {FEATURES.map((f) => (
          <div key={f.title}>
            <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '0.6rem' }}>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </section>
    </main>
  )
}
