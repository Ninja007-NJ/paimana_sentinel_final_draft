import { reliabilityLevel } from "../utils/reliability";

export function ReliabilityBadge({ score }: { score: number | null | undefined }) {
  const level = reliabilityLevel(score);
  return (
    <span 
      className={`badge reliability-badge reliability-${level.toLowerCase()}`} 
      title="Data reliability score (0-100), separate from delay probability"
    >
      <span className="reliability-indicator" />
      {score == null ? "Not available" : `${level} · ${score.toFixed(0)}`}
    </span>
  );
}
