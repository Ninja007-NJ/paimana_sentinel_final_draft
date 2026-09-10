import type { LucideIcon } from "lucide-react";

export function StatCard({ 
  label, 
  value, 
  helper, 
  icon: Icon, 
  tone = "blue" 
}: { 
  label: string; 
  value: string; 
  helper: string; 
  icon: LucideIcon; 
  tone?: string;
}) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <div className="stat-header">
        <span className="stat-label">{label}</span>
        <div className="stat-icon">
          <Icon size={18} />
        </div>
      </div>
      <div className="stat-content">
        <strong className="stat-value">{value}</strong>
        <small className="stat-helper">{helper}</small>
      </div>
    </article>
  );
}
