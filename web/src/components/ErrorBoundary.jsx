import { Component } from 'react'

/** Keeps a crash in one view from unmounting the whole app; resets when `resetKey` changes. */
export default class ErrorBoundary extends Component {
  state = { error: null, key: this.props.resetKey }

  static getDerivedStateFromError(error) {
    return { error }
  }

  static getDerivedStateFromProps(props, state) {
    return props.resetKey === state.key ? null : { key: props.resetKey, error: null }
  }

  componentDidCatch(error) {
    console.error(`View "${this.props.name}" crashed:`, error)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="view-error">
        <b>{this.props.name} failed to render.</b> {String(this.state.error.message ?? this.state.error)}
      </div>
    )
  }
}
