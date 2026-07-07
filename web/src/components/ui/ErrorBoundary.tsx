import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) {
      return this.props.fallback(error, this.reset);
    }

    return (
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-md rounded border border-red-200 dark:border-red-800 bg-card overflow-hidden shadow">
          {/* Header stripe */}
          <div className="h-1 bg-red-500" />

          <div className="px-6 py-5">
            <div className="flex items-start gap-3">
              {/* Icon */}
              <div className="mt-0.5 flex-shrink-0 w-8 h-8 rounded bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 flex items-center justify-center">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  className="text-red-500"
                >
                  <path
                    d="M8 1L15 14H1L8 1Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                  <path d="M8 6v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <circle cx="8" cy="11.5" r="0.75" fill="currentColor" />
                </svg>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono font-semibold uppercase tracking-widest text-red-500 mb-1">
                  Render Error
                </p>
                <p className="text-sm text-foreground font-mono leading-relaxed break-words">
                  {error.message || 'An unexpected error occurred.'}
                </p>
              </div>
            </div>

            {/* Stack hint */}
            {error.stack && (
              <details className="mt-4">
                <summary className="text-xs font-mono text-muted-foreground cursor-pointer hover:text-foreground transition-colors select-none">
                  Stack trace
                </summary>
                <pre className="mt-2 text-xs font-mono text-muted-foreground overflow-x-auto whitespace-pre-wrap bg-muted rounded p-3 border border-border">
                  {error.stack}
                </pre>
              </details>
            )}

            {/* Action */}
            <button
              onClick={this.reset}
              className="
                mt-4 w-full px-4 py-2 rounded text-sm font-mono font-semibold
                bg-muted hover:bg-muted/80
                text-foreground
                border border-border
                transition-colors focus:outline-none focus:ring-2 focus:ring-primary
              "
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }
}
