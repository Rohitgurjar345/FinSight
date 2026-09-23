import React from 'react'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer style={{ borderTop: '1px solid var(--border)', marginTop: 'var(--space-5)' }}>
      <div
        className="container"
        style={{
          padding: 'var(--space-3) var(--space-3)',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1.5rem',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ color: 'var(--muted)', fontSize: 'var(--text-xs)' }}>
          Ledger is a local tool for understanding your own spending. It does not send your data anywhere.
        </span>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <Link to="/privacy" style={{ fontSize: 'var(--text-sm)', color: 'var(--muted)' }}>Privacy policy</Link>
          <Link to="/terms" style={{ fontSize: 'var(--text-sm)', color: 'var(--muted)' }}>Terms and conditions</Link>
        </div>
      </div>
    </footer>
  )
}
