import { Component, ReactNode } from 'react'

interface Props {
  fallback?: ReactNode
  children: ReactNode
}

interface State {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('模块渲染失败', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <section className="card error-card">
          <div className="section-title"><span>!</span><div><h2>模块加载失败</h2><p>请刷新页面后重试。</p></div></div>
          <button onClick={() => this.setState({ hasError: false })} className="text-button">重新加载此模块</button>
        </section>
      )
    }
    return this.props.children
  }
}
