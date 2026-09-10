export type ReliabilityLevel = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export function reliabilityLevel(score: number | null | undefined): ReliabilityLevel {
  if (score == null) return "UNKNOWN";
  if (score >= 85) return "HIGH";
  if (score >= 65) return "MEDIUM";
  return "LOW";
}
