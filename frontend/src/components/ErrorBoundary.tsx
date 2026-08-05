import React, { Component, type ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

type Props = {
  children: ReactNode
  fallbackTitle?: string
  fallbackMessage?: string
}

type State = {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full w-full flex-col items-center justify-center p-6 text-center">
          <div className="flex max-w-md flex-col items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-6 shadow-sm">
            <AlertCircle className="size-10 text-destructive" />
            <h2 className="text-lg font-semibold text-foreground">
              {this.props.fallbackTitle ?? 'Something went wrong'}
            </h2>
            <p className="text-xs text-muted-foreground">
              {this.props.fallbackMessage ??
                'An unexpected error occurred in this section of the application.'}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2 gap-2"
              onClick={this.handleReload}
            >
              <RefreshCw className="size-3.5" />
              Reload Section
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
