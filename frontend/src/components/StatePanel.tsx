import type { ReactNode } from "react";
import { AlertCircle, Inbox, LoaderCircle, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Loading PAIMANA data…" }: { label?: string }) {
  return <div className="state-panel"><LoaderCircle className="spin" aria-hidden="true" /><strong>{label}</strong><span>Please wait while the frozen project records are prepared.</span></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="state-panel error-state" role="alert"><AlertCircle aria-hidden="true" /><strong>Unable to load this view</strong><span>{message}</span>{onRetry && <button className="secondary-button" onClick={onRetry}><RefreshCw size={15} /> Retry</button>}</div>;
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="state-panel"><Inbox aria-hidden="true" /><strong>{title}</strong>{children && <span>{children}</span>}</div>;
}
