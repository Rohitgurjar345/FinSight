import React, { useState, useRef } from 'react'
import GlassPanel from '../components/GlassPanel.jsx'
import { uploadFiles, getHealthScore, getLoanPreassessment, askAssistant } from '../api/client.js'

export default function Dashboard() {
  const [sessionId, setSessionId] = useState(null)
  const [uploadState, setUploadState] = useState({ status: 'idle', error: null, report: null })
  const [healthScore, setHealthScore] = useState(null)
  const [healthScoreError, setHealthScoreError] = useState(null)
  const fileInputRef = useRef(null)

  async function handleFilesSelected(e) {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    setUploadState({ status: 'loading', error: null, report: null })
    setHealthScore(null)
    setHealthScoreError(null)

    try {
      const result = await uploadFiles(files)
      setSessionId(result.session_id)
      setUploadState({ status: 'done', error: null, report: result })

      try {
        const hs = await getHealthScore(result.session_id)
        setHealthScore(hs)
      } catch (err) {
        setHealthScoreError(err.message)
      }
    } catch (err) {
      setUploadState({ status: 'error', error: err.message, report: null })
    }
  }

  return (
    <main className="container" style={{ padding: '2.5rem 1.5rem 4rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)' }}>Dashboard</h1>
        <p style={{ marginTop: '0.5rem' }}>Upload one or more bank statements to get started.</p>
      </div>

      <UploadCard
        uploadState={uploadState}
        fileInputRef={fileInputRef}
        onFilesSelected={handleFilesSelected}
      />

      {sessionId && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', alignItems: 'start' }}>
          <HealthScoreCard healthScore={healthScore} error={healthScoreError} />
          <LoanCard sessionId={sessionId} />
        </div>
      )}

      {sessionId && <ChatCard sessionId={sessionId} />}
    </main>
  )
}

function UploadCard({ uploadState, fileInputRef, onFilesSelected }) {
  return (
    <GlassPanel cornerRadius={20} style={{ padding: '2rem' }}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.xlsx,.xls,.pdf"
        onChange={onFilesSelected}
        style={{ display: 'none' }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ fontSize: 'var(--text-lg)' }}>Upload statements</h3>
          <p style={{ marginTop: '0.4rem' }}>CSV, Excel, or PDF. Select more than one file to upload them together.</p>
        </div>
        <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>
          Choose files
        </button>
      </div>

      {uploadState.status === 'loading' && (
        <p style={{ marginTop: '1.25rem', color: 'var(--signal)' }}>Processing your statement(s)…</p>
      )}
      {uploadState.status === 'error' && (
        <p style={{ marginTop: '1.25rem', color: 'var(--caution)' }}>{uploadState.error}</p>
      )}
      {uploadState.status === 'done' && uploadState.report && (
        <div style={{ marginTop: '1.25rem', fontSize: 'var(--text-sm)', color: 'var(--muted)' }}>
          <span className="numeric">{uploadState.report.transaction_count}</span> transactions loaded from{' '}
          <span className="numeric">{uploadState.report.ingestion_report.files_processed}</span> file(s).
          {uploadState.report.ingestion_report.files_failed > 0 && (
            <span style={{ color: 'var(--caution)' }}>
              {' '}{uploadState.report.ingestion_report.files_failed} file(s) failed to process.
            </span>
          )}
        </div>
      )}
    </GlassPanel>
  )
}

function HealthScoreCard({ healthScore, error }) {
  return (
    <GlassPanel cornerRadius={20} style={{ padding: '1.75rem' }}>
      <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '1rem' }}>Financial health score</h3>

      {error && <p style={{ color: 'var(--caution)' }}>{error}</p>}

      {!error && !healthScore && <p>Calculating…</p>}

      {healthScore && (
        <>
          <div className="numeric" style={{ fontSize: 'var(--text-3xl)', color: 'var(--signal)' }}>
            {healthScore.score}
          </div>
          <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {Object.entries(healthScore.breakdown || {}).map(([key, d]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)' }}>
                <span style={{ color: 'var(--muted)' }}>{key.replaceAll('_', ' ')}</span>
                <span className="numeric">{d.healthy_percentile}th percentile</span>
              </div>
            ))}
          </div>
          {healthScore.estimation_warnings && healthScore.estimation_warnings.length > 0 && (
            <details style={{ marginTop: '1.25rem' }}>
              <summary style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)', cursor: 'pointer' }}>
                {healthScore.estimation_warnings.length} assumption(s) behind this estimate
              </summary>
              <ul style={{ marginTop: '0.6rem', paddingLeft: '1.1rem', fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>
                {healthScore.estimation_warnings.map((w, i) => <li key={i} style={{ marginBottom: '0.4rem' }}>{w}</li>)}
              </ul>
            </details>
          )}
        </>
      )}
    </GlassPanel>
  )
}

function LoanCard({ sessionId }) {
  const [fields, setFields] = useState({ age: '', credit_score: '', assets: '', existing_loan: '0', criminal_record: '0' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  function update(key, value) {
    setFields((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await getLoanPreassessment(sessionId, {
        age: Number(fields.age),
        credit_score: Number(fields.credit_score),
        assets: Number(fields.assets),
        existing_loan: Number(fields.existing_loan),
        criminal_record: Number(fields.criminal_record),
      })
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassPanel cornerRadius={20} style={{ padding: '1.75rem' }}>
      <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '0.4rem' }}>Loan pre-assessment</h3>
      <p style={{ marginBottom: '1.25rem' }}>
        These fields can't be worked out from a bank statement, so they're asked directly.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.9rem' }}>
        <div>
          <label className="field-label">Age</label>
          <input className="field-input" type="number" required value={fields.age} onChange={(e) => update('age', e.target.value)} />
        </div>
        <div>
          <label className="field-label">Credit score</label>
          <input className="field-input" type="number" required value={fields.credit_score} onChange={(e) => update('credit_score', e.target.value)} />
        </div>
        <div>
          <label className="field-label">Assets (value)</label>
          <input className="field-input" type="number" required value={fields.assets} onChange={(e) => update('assets', e.target.value)} />
        </div>
        <div>
          <label className="field-label">Existing loan?</label>
          <select className="field-input" value={fields.existing_loan} onChange={(e) => update('existing_loan', e.target.value)}>
            <option value="0">No</option>
            <option value="1">Yes</option>
          </select>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label className="field-label">Criminal record?</label>
          <select className="field-input" value={fields.criminal_record} onChange={(e) => update('criminal_record', e.target.value)}>
            <option value="0">No</option>
            <option value="1">Yes</option>
          </select>
        </div>
        <button type="submit" className="btn btn-primary" style={{ gridColumn: '1 / -1' }} disabled={loading}>
          {loading ? 'Checking…' : 'Check readiness'}
        </button>
      </form>

      {error && <p style={{ marginTop: '1rem', color: 'var(--caution)' }}>{error}</p>}

      {result && (
        <div style={{ marginTop: '1.25rem' }}>
          <div className="numeric" style={{ fontSize: 'var(--text-xl)', textTransform: 'capitalize' }}>
            {result.readiness_tier.replaceAll('_', ' ')}
          </div>
          <p style={{ marginTop: '0.5rem', fontSize: 'var(--text-xs)' }}>{result.disclaimer}</p>
        </div>
      )}
    </GlassPanel>
  )
}

function ChatCard({ sessionId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSend(e) {
    e.preventDefault()
    const query = input.trim()
    if (!query) return

    setMessages((m) => [...m, { role: 'user', text: query }])
    setInput('')
    setLoading(true)

    try {
      const res = await askAssistant(sessionId, query)
      setMessages((m) => [...m, { role: 'assistant', text: res.answer, source: res.source }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', text: err.message, source: 'error' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassPanel cornerRadius={20} style={{ padding: '1.75rem' }}>
      <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '1rem' }}>Ask about your spending</h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: 320, overflowY: 'auto', marginBottom: '1rem' }}>
        {messages.length === 0 && (
          <p>Try: "what is my total spend?" or "how much did I spend on food last month?"</p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                background: m.role === 'user' ? 'var(--surface-raised)' : 'transparent',
                border: m.role === 'user' ? '1px solid var(--border)' : 'none',
                borderRadius: 'var(--radius-sm)',
                padding: m.role === 'user' ? '0.6rem 0.9rem' : 0,
                maxWidth: '80%',
                color: m.source === 'error' ? 'var(--caution)' : 'var(--paper)',
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.75rem' }}>
        <input
          className="field-input"
          style={{ fontFamily: 'var(--font-body)' }}
          placeholder="Ask a question about your spending"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </GlassPanel>
  )
}
