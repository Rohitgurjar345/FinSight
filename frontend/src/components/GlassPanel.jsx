import React from 'react'
import LiquidGlass from 'liquid-glass-react'

/**
 * Thin wrapper around liquid-glass-react, scoped to this project's rules:
 * - cornerRadius always rounded-rectangle (never a pill/capsule shape)
 * - used only for nav and summary cards, never wrapped around live data
 *   (tables, charts) per the project's own performance/legibility decision
 *
 * If the liquid-glass-react import fails to render for any reason (e.g. a
 * browser without the needed CSS features), this falls back to a plain
 * backdrop-blur card so the page never breaks — it just loses the glass
 * refraction detail, which is a fine degradation for a finance dashboard
 * where the content matters more than the effect.
 */
export default function GlassPanel({ children, cornerRadius = 22, className = '', style = {}, ...rest }) {
  const [hasError, setHasError] = React.useState(false)

  if (hasError) {
    return (
      <div
        className={className}
        style={{
          background: 'rgba(27, 34, 46, 0.72)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(234, 238, 243, 0.12)',
          borderRadius: cornerRadius,
          ...style,
        }}
      >
        {children}
      </div>
    )
  }

  return (
    <GlassErrorBoundary onError={() => setHasError(true)}>
      <LiquidGlass
        cornerRadius={cornerRadius}
        blurAmount={0.12}
        saturation={110}
        aberrationIntensity={1}
        elasticity={0.15}
        className={className}
        style={style}
        {...rest}
      >
        {children}
      </LiquidGlass>
    </GlassErrorBoundary>
  )
}

class GlassErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { errored: false }
  }
  static getDerivedStateFromError() {
    return { errored: true }
  }
  componentDidCatch() {
    this.props.onError()
  }
  render() {
    if (this.state.errored) return null
    return this.props.children
  }
}
