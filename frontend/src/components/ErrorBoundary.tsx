import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./StatePanel";

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error("PAIMANA view error", error, info); }

  render() {
    if (this.state.error) return <ErrorState message="This view encountered an unexpected presentation error." onRetry={() => window.location.reload()} />;
    return this.props.children;
  }
}
