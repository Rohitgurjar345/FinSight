import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import GlassPanel from './GlassPanel.jsx'

const LINKS = [
  { to: '/', label: 'Ledger' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function Nav() {
  const location = useLocation()

  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 50, padding: '1rem 0' }}>
      <div className="container">
        <GlassPanel cornerRadius={18} style={{ padding: '0.75rem 1.25rem' }}>
          <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Link to="/" style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.05rem' }}>
              Ledger
            </Link>
            <div style={{ display: 'flex', gap: '1.75rem', alignItems: 'center' }}>
              <Link
                to="/dashboard"
                style={{
                  fontSize: 'var(--text-sm)',
                  color: location.pathname === '/dashboard' ? 'var(--paper)' : 'var(--muted)',
                }}
              >
                Dashboard
              </Link>
              <Link to="/dashboard" className="btn btn-primary" style={{ padding: '0.55rem 1.1rem' }}>
                Open the dashboard
              </Link>
            </div>
          </nav>
        </GlassPanel>
      </div>
    </div>
  )
}
