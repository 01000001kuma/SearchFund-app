import React from "react"
import { Button } from "@/components/ui/button"

interface Props {
  children: React.ReactNode
  fallback?: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <p className="text-lg font-medium text-red-600">
            Algo salió mal
          </p>
          <p className="text-sm text-muted-foreground">
            {this.state.error?.message || "Error inesperado"}
          </p>
          <Button
            variant="outline"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
          >
            Recargar
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
