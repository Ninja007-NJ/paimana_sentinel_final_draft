import type { RiskLevel } from "../types";

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={`badge risk-badge risk-${level.toLowerCase()}`}>
      <span className="badge-dot" />
      {level}
    </span>
  );
}
