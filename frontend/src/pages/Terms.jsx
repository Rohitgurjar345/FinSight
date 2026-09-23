import React from 'react'
import GlassPanel from '../components/GlassPanel.jsx'

export default function Terms() {
  return (
    <main className="container" style={{ padding: '3rem 1.5rem 4rem', maxWidth: 760 }}>
      <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: '1rem' }}>Terms and conditions</h1>

      <GlassPanel cornerRadius={16} style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <p style={{ fontSize: 'var(--text-sm)' }}>
          This is a draft written to match what Ledger currently does. It has not
          been reviewed by a lawyer. Have it reviewed before relying on it for a
          real deployment.
        </p>
      </GlassPanel>

      <Section title="What Ledger is">
        <p>
          Ledger categorizes transactions, estimates a financial health score, gives
          a loan pre-assessment, and answers questions about your own uploaded data.
          It is a local analysis tool, not a bank, lender, or financial advisor.
        </p>
      </Section>

      <Section title="The loan pre-assessment is not a loan decision">
        <p>
          The loan readiness tier is an automated estimate from a model trained on
          synthetic data. It does not reflect the decision of any real lender and
          should not be treated as one. Every result includes this same disclaimer
          directly alongside it.
        </p>
      </Section>

      <Section title="The health score and forecasts are estimates">
        <p>
          Category totals, the health score, and any spending forecasts are built
          from automatic categorization of your statement, which is not perfectly
          accurate. Treat these numbers as a starting point for your own judgment,
          not a certified financial assessment.
        </p>
      </Section>

      <Section title="No warranty">
        <p>
          This software is provided as-is, without warranty of any kind, including
          accuracy of categorization, scoring, or any figure it produces.
        </p>
      </Section>

      <Section title="Changes">
        <p>
          These terms may change as the application changes. Continued use after a
          change means you accept the updated terms.
        </p>
      </Section>
    </main>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '1.75rem' }}>
      <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: '0.5rem' }}>{title}</h2>
      {children}
    </div>
  )
}
