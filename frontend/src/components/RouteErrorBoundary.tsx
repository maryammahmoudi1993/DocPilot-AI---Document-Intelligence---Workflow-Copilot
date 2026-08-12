import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorState } from '@/components/ui/ErrorState';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/** Route-scoped, unlike the app-wide `ErrorBoundary` (which replaces the
 * entire shell, sidebar included). A single page crashing — e.g. a
 * malformed API response a component didn't defensively handle — should
 * not also take out navigation the user needs to get somewhere else;
 * this renders inside AppShell's `<main>` only, so the sidebar/header
 * stay usable. "Try again" resets local state and re-renders the
 * subtree rather than a full page reload, which is enough to recover
 * from most transient render errors. */
export class RouteErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Route render error:', error, errorInfo);
  }

  private handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <ErrorState
            title="This page couldn't be displayed"
            description="Something went wrong rendering this page. Try again, or navigate elsewhere."
            onRetry={this.handleRetry}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
