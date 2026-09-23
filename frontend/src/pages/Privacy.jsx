import React from 'react'
import GlassPanel from '../components/GlassPanel.jsx'

export default function Privacy() {
  return (
    <main className="container" style={{ padding: '3rem 1.5rem 4rem', maxWidth: 760 }}>
      <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: '1rem' }}>Privacy policy</h1>

      <GlassPanel cornerRadius={16} style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <p style={{ fontSize: 'var(--text-sm)' }}>
          This is a draft written to describe how Ledger actually works today. It has
          not been reviewed by a lawyer. Before relying on this for a real product handling
          real people's financial data, have it reviewed by one — especially if you operate
          in a jurisdiction with specific financial-data or privacy regulations (e.g. GDPR, DPDP Act).
        </p>
      </GlassPanel>

      <Section title="What happens to your data">
        <p>
          When you upload a bank statement, it is parsed and held in memory by the
          server process running on your own machine, for the duration of that
          server session. It is not uploaded to any third-party cloud service by
          this application.
        </p>
      </Section>

      <Section title="The one exception: the assistant">
        <p>
          If you configure an Anthropic API key to enable live answers from the
          chat assistant, the transactions relevant to your specific question are
          sent to Anthropic's API to generate a response. If no key is configured,
          questions are answered entirely locally by direct calculation on your
          data, and nothing is sent anywhere.
        </p>
      </Section>

      <Section title="Storage and retention">
        <p>
          Uploaded files are currently written to a temporary folder on the server
          and held in memory for the session. Restarting the server clears all
          session data. There is no database, backup, or long-term storage in the
          current version of this application.
        </p>
      </Section>

      <Section title="What this doesn't cover">
        <p>
          This policy describes the application as built for local/development use.
          It does not cover any hosted, multi-user, or production deployment — those
          would need their own review of storage, encryption, access control, and
          applicable law before this policy could honestly apply to them.
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
