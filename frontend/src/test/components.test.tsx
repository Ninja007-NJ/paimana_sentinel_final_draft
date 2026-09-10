import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { RiskBadge } from "../components/RiskBadge";

test("risk and reliability are visibly separate concepts", () => {
  render(<><RiskBadge level="CRITICAL" /><ReliabilityBadge score={91} /></>);
  expect(screen.getByText("CRITICAL")).toHaveClass("risk-badge");
  expect(screen.getByText(/HIGH/)).toHaveClass("reliability-badge");
});

test.each(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const)("risk badge maps %s to its visual class", (level) => {
  render(<RiskBadge level={level} />);
  expect(screen.getByText(level)).toHaveClass(`risk-${level.toLowerCase()}`);
});

test("reliability handles missing scores", () => {
  render(<ReliabilityBadge score={null} />);
  expect(screen.getByText("Not available")).toBeInTheDocument();
});
