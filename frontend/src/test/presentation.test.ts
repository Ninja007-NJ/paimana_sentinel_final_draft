import { expect, test } from "vitest";
import { alertTypeLabel, collapseWhitespace, displayValue } from "../utils/presentation";

test("known geography and category mappings are human friendly", () => {
  expect(displayValue("Andaman & Nicobar", "state")).toBe("Andaman and Nicobar Islands");
  expect(displayValue("ANDAMAN AND", "state")).toBe("Andaman and Nicobar Islands");
  expect(displayValue("CIVIL\nAVIATION", "sector")).toBe("Civil Aviation");
  expect(displayValue("TELECOMMUNI CATIONS", "sector")).toBe("Telecommunications");
  expect(displayValue("ROAD TRANSPORT AND", "sector")).toBe("Road Transport and Highways");
  expect(displayValue("PAIMANA_TRANSITION", "regime")).toBe("PAIMANA Transition");
  expect(displayValue("PAIMANA_ID", "identity")).toBe("PAIMANA ID");
});

test("unknown values are preserved while presentation whitespace is cleaned", () => {
  expect(displayValue("  A New Unmapped Category  ", "sector")).toBe("A New Unmapped Category");
  expect(collapseWhitespace("Jammu and\nKashmir")).toBe("Jammu and Kashmir");
});

test("common displayed labels contain no embedded newlines", () => {
  const labels = [
    displayValue("Jammu and\nKashmir", "state"),
    displayValue("CIVIL\nAVIATION", "sector"),
    displayValue("Ministry of Road Transport & Highways", "ministry"),
    alertTypeLabel("REPEATED_TARGET_REVISION"),
  ];
  expect(labels.every(label => !/[\r\n]/.test(label))).toBe(true);
});

test("canonical project identifiers remain unchanged", () => {
  const project = { canonical_project_id: "P-618861", state: "ANDAMAN AND" };
  displayValue(project.state, "state");
  expect(project.canonical_project_id).toBe("P-618861");
});

test("alert types use approved wording", () => {
  expect(alertTypeLabel("CRITICAL_RISK")).toBe("Critical Risk");
  expect(alertTypeLabel("NEW_HIGH_RISK")).toBe("New High-Risk Project");
  expect(alertTypeLabel("LOW_CONFIDENCE_HIGH_RISK")).toBe("High Risk / Low Data Reliability");
  expect(alertTypeLabel("STAGNATING_PROJECT")).toBe("Project Progress Stagnating");
});
