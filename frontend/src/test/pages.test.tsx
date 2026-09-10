import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { DashboardPage } from "../pages/DashboardPage";
import { ProjectDetailPage } from "../pages/ProjectDetailPage";
import { ProjectExplorerPage } from "../pages/ProjectExplorerPage";
import { AlertsPage } from "../pages/AlertsPage";
import { PortfolioAnalyticsPage } from "../pages/PortfolioAnalyticsPage";
import { InterventionPriorityPage } from "../pages/InterventionPriorityPage";
import { alerts, detail, explanation, peers, priority, project, riskRow, scenarios, trajectory, whatIfConfig } from "./fixtures";

vi.mock("../api/client", () => ({ api: { getProjects: vi.fn(), getProject: vi.fn(), getTrajectory: vi.fn(), getExplanation: vi.fn(), hydratePortfolioRisk: vi.fn(), getPeers: vi.fn(), getAlerts: vi.fn(), getProjectAlerts: vi.fn(), getWhatIfConfig: vi.fn(), runWhatIf: vi.fn(), getScenarios: vi.fn(), getPortfolioAnalytics: vi.fn(), getSectorAnalytics: vi.fn(), getMinistryAnalytics: vi.fn(), getStateAnalytics: vi.fn(), getPriorities: vi.fn(), getProjectPriority: vi.fn(), askAssistant: vi.fn() } }));

beforeEach(() => {
  vi.mocked(api.getProjects).mockResolvedValue([project]);
  vi.mocked(api.getProject).mockResolvedValue(detail);
  vi.mocked(api.getTrajectory).mockResolvedValue(trajectory);
  vi.mocked(api.getExplanation).mockResolvedValue(explanation);
  vi.mocked(api.getPeers).mockResolvedValue(peers);
  vi.mocked(api.getAlerts).mockResolvedValue(alerts);
  vi.mocked(api.getProjectAlerts).mockResolvedValue(alerts);
  vi.mocked(api.getWhatIfConfig).mockResolvedValue(whatIfConfig);
  vi.mocked(api.getScenarios).mockResolvedValue(scenarios);
  vi.mocked(api.getPortfolioAnalytics).mockResolvedValue({ summary: { project_count: 1, average_delay_risk: .61, median_delay_risk: .61, high_risk_count: 1, high_risk_percentage: 100, critical_risk_count: 1, rapidly_rising_risk_count: 0, average_data_reliability: 91, aggregate_original_cost_cr: 1000, aggregate_current_cost_cr: 1200, aggregate_expenditure_cr: 600, active_alert_count: 1 }, latest_snapshot_month: "2026-01", risk_distribution: [{ risk_level: "CRITICAL", count: 1 }], risk_trend: [{ snapshot_month: "2026-01", project_count: 1, average_delay_risk: .61, high_or_critical_count: 1 }], minimum_group_size: 10 });
  vi.mocked(api.getSectorAnalytics).mockResolvedValue([]);
  vi.mocked(api.getMinistryAnalytics).mockResolvedValue([]);
  vi.mocked(api.getStateAnalytics).mockResolvedValue([]);
  vi.mocked(api.getPriorities).mockResolvedValue([priority]);
  vi.mocked(api.getProjectPriority).mockResolvedValue(priority);
  vi.mocked(api.askAssistant).mockResolvedValue({ answer: "Grounded assistant answer.", scope: "project", project_id: "P-001", provider: "deterministic-fallback", model: "google/gemma-4-26b-a4b-it:free", grounded: true, sources_used: ["prediction_3m", "prediction_6m", "shap"] });
  vi.mocked(api.hydratePortfolioRisk).mockImplementation(async (_projects, onProgress) => { onProgress?.(1, 1, [riskRow]); return [riskRow]; });
});

test("dashboard renders portfolio metrics and priority projects", async () => {
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);
  expect(await screen.findByText("Infrastructure Risk Dashboard")).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByText("National Corridor Project").length).toBeGreaterThan(0));
  expect(screen.getByText("Average 3-Month Delay Risk")).toBeInTheDocument();
  expect(screen.getByText("Recent alerts")).toBeInTheDocument();
});

test("explorer exposes required filters and table", async () => {
  render(<MemoryRouter><ProjectExplorerPage /></MemoryRouter>);
  expect(await screen.findByText("Project Explorer")).toBeInTheDocument();
  expect(screen.getByText("Ministry / Department")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Data reliability" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Data Reliability" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /National Corridor Project P-001/i })).toHaveAttribute("href", "/projects/P-001");
});

test("project explorer opens detail with the canonical project identifier", async () => {
  render(<MemoryRouter initialEntries={["/projects"]}><Routes><Route path="/projects" element={<ProjectExplorerPage />} /><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  fireEvent.click(await screen.findByRole("link", { name: /National Corridor Project P-001/i }));
  expect(await screen.findByRole("heading", { name: "National Corridor Project" })).toBeInTheDocument();
  expect(api.getProject).toHaveBeenCalledWith("P-001");
});

test("project explorer applies a state passed from the dashboard map", async () => {
  render(<MemoryRouter initialEntries={["/projects?state=Maharashtra"]}><ProjectExplorerPage /></MemoryRouter>);
  expect(await screen.findByRole("link", { name: /National Corridor Project P-001/i })).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "State" })).toHaveValue("Maharashtra");
  expect(screen.getByText("1 projects")).toBeInTheDocument();
});

test("project detail renders trajectory, explanations, and disclaimer", async () => {
  render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("National Corridor Project")).toBeInTheDocument();
  expect(screen.getByText("3-Month Delay-Risk Trajectory")).toBeInTheDocument();
  expect(screen.getByText("Factors increasing risk")).toBeInTheDocument();
  expect(screen.getByText("6-Month Delay Risk")).toBeInTheDocument();
  expect(screen.getByText("74%")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Project Intelligence Assistant" })).toBeInTheDocument();
  expect(screen.getByText("Peer Comparison")).toBeInTheDocument();
  expect(screen.getByText("What-If Simulator")).toBeInTheDocument();
  expect(screen.getByText("Suggested Scenarios")).toBeInTheDocument();
  expect(screen.getByText("Risk Trend & Intervention Priority")).toBeInTheDocument();
  expect(screen.getByText("+12.0 pp")).toBeInTheDocument();
  expect(screen.getByText("+27.0 pp")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Load into simulator" }));
  expect(screen.getByRole("spinbutton", { name: "Expected physical progress velocity numeric value" })).toHaveValue(4);
  expect(screen.getByRole("button", { name: "Reset" })).toBeInTheDocument();
  expect(screen.getByText("Risk estimates are predictive decision-support signals and do not establish causality.")).toBeInTheDocument();
});

test("suggested scenarios render the existing full cards when recommendations are available", async () => {
  const { container } = render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Suggested Scenarios" })).toBeInTheDocument();
  expect(screen.getAllByText("Expected physical progress velocity").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Load into simulator" })).toBeInTheDocument();
  expect(container.querySelector(".scenario-grid")).toBeInTheDocument();
  expect(screen.getAllByText(whatIfConfig.disclaimer).length).toBeGreaterThan(0);
});

test("suggested scenarios use a compact empty state without an empty card grid", async () => {
  vi.mocked(api.getScenarios).mockResolvedValueOnce({ ...scenarios, recommendations: [] });
  const { container } = render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("No suitable model-based scenario identified")).toBeInTheDocument();
  expect(screen.getByText("No safe single-feature adjustment produced a lower model-estimated risk for this project.")).toBeInTheDocument();
  expect(container.querySelector(".scenario-grid")).not.toBeInTheDocument();
  expect(container.querySelector(".scenario-panel .state-panel")).not.toBeInTheDocument();
  expect(screen.getAllByText(whatIfConfig.disclaimer).length).toBeGreaterThan(0);
});

test("scenario API failure degrades compactly while Project Detail and What-If remain available", async () => {
  vi.mocked(api.getScenarios).mockRejectedValueOnce(new Error("scenario backend unavailable"));
  const { container } = render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "National Corridor Project" })).toBeInTheDocument();
  expect(await screen.findByText("Scenario analysis is currently unavailable.")).toBeInTheDocument();
  expect(screen.getByText("What-If Simulator")).toBeInTheDocument();
  expect(screen.getByText("3-Month Delay-Risk Trajectory")).toBeInTheDocument();
  expect(container.querySelector(".scenario-panel .state-panel")).not.toBeInTheDocument();
  expect(screen.getByText("Scenario estimates reflect model behavior under modified inputs and do not imply guaranteed causal impact.")).toBeInTheDocument();
});

test.each([
  ["trajectory", () => vi.mocked(api.getTrajectory).mockRejectedValueOnce(new Error("trajectory unavailable")), "Risk trajectory could not be loaded."],
  ["peer comparison", () => vi.mocked(api.getPeers).mockRejectedValueOnce(new Error("peers unavailable")), "Peer comparison could not be loaded."],
  ["project alerts", () => vi.mocked(api.getProjectAlerts).mockRejectedValueOnce(new Error("alerts unavailable")), "Project warnings could not be loaded."],
])("project detail core remains visible when %s fails", async (_name, fail, message) => {
  fail();
  render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "National Corridor Project" })).toBeInTheDocument();
  expect(await screen.findByText(message)).toBeInTheDocument();
  expect(screen.getByText("Financial position")).toBeInTheDocument();
});

test("early warning centre renders deterministic alerts", async () => {
  render(<MemoryRouter><AlertsPage /></MemoryRouter>);
  expect(await screen.findByText("Early Warning Centre")).toBeInTheDocument();
  expect(screen.getAllByText("Critical Risk").length).toBeGreaterThan(0);
  expect(screen.getByText("Intervention Priority")).toBeInTheDocument();
});

test("intervention queue renders deterministic ranking and canonical navigation", async () => {
  render(<MemoryRouter initialEntries={["/priorities"]}><Routes><Route path="/priorities" element={<InterventionPriorityPage />} /><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Intervention Priority" })).toBeInTheDocument();
  expect(screen.getByText("#1")).toBeInTheDocument();
  expect(screen.getByText("94.0 / 100")).toBeInTheDocument();
  expect(screen.getByText("Not a probability")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: /National Corridor Project P-001/i }));
  expect(await screen.findByRole("heading", { name: "National Corridor Project" })).toBeInTheDocument();
  expect(api.getProject).toHaveBeenCalledWith("P-001");
});

test("early warning centre renders an empty state", async () => {
  vi.mocked(api.getAlerts).mockResolvedValueOnce([]);
  render(<MemoryRouter><AlertsPage /></MemoryRouter>);
  expect(await screen.findByText("No active alerts")).toBeInTheDocument();
});

test("early warning centre distinguishes a filtered empty state", async () => {
  render(<MemoryRouter><AlertsPage /></MemoryRouter>);
  await screen.findByText("Early Warning Centre");
  fireEvent.change(screen.getByRole("combobox", { name: "Severity" }), { target: { value: "INFO" } });
  expect(screen.getByText("No alerts match these filters")).toBeInTheDocument();
});

test("early warning project navigation uses the canonical identifier", async () => {
  render(<MemoryRouter initialEntries={["/alerts"]}><Routes><Route path="/alerts" element={<AlertsPage />} /><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  fireEvent.click(await screen.findByRole("link", { name: "Open National Corridor Project" }));
  expect(await screen.findByRole("heading", { name: "National Corridor Project" })).toBeInTheDocument();
  expect(api.getProject).toHaveBeenCalledWith("P-001");
});

test("portfolio analytics renders management view", async () => {
  render(<MemoryRouter><PortfolioAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByText("Portfolio Analytics")).toBeInTheDocument();
  expect(screen.getByText("Portfolio risk distribution")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Project Intelligence Assistant" })).toBeInTheDocument();
});

test("project assistant submits one grounded question and displays transparency", async () => {
  render(<MemoryRouter initialEntries={["/projects/P-001"]}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("heading", { name: "Project Intelligence Assistant" });
  fireEvent.click(screen.getByRole("button", { name: "Compare the 3-month and 6-month risks." }));
  expect(screen.getByRole("textbox", { name: "Assistant question" })).toHaveValue("Compare the 3-month and 6-month risks.");
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
  expect(await screen.findByText("Grounded assistant answer.")).toBeInTheDocument();
  expect(api.askAssistant).toHaveBeenCalledWith("Compare the 3-month and 6-month risks.", "P-001");
  expect(screen.getByText("Answers are generated from PAIMANA Sentinel's structured analytics and model outputs. The assistant does not independently calculate project risk.")).toBeInTheDocument();
});

test("assistant renders markdown emphasis and bullets as formatted text", async () => {
  vi.mocked(api.askAssistant).mockResolvedValueOnce({ answer: "Summary\n\n- **CRITICAL_RISK** – 766 alerts", scope: "portfolio", project_id: null, provider: "openrouter", model: "test", grounded: true, sources_used: ["alerts"] });
  render(<MemoryRouter><PortfolioAnalyticsPage /></MemoryRouter>);
  fireEvent.change(await screen.findByRole("textbox", { name: "Assistant question" }), { target: { value: "review priorities" } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
  expect(await screen.findByText("CRITICAL_RISK")).toBeInTheDocument();
  expect(screen.getByText("CRITICAL_RISK").tagName).toBe("STRONG");
  expect(screen.getByRole("list")).toBeInTheDocument();
  expect(screen.queryByText("**CRITICAL_RISK**")).not.toBeInTheDocument();
});

test("portfolio remains usable when one analytics endpoint fails", async () => {
  vi.mocked(api.getStateAnalytics).mockRejectedValueOnce(new Error("states unavailable"));
  render(<MemoryRouter><PortfolioAnalyticsPage /></MemoryRouter>);
  expect(await screen.findByText("Portfolio Analytics")).toBeInTheDocument();
  expect(screen.getByText("Portfolio risk distribution")).toBeInTheDocument();
  expect(await screen.findByText("State comparison could not be loaded.")).toBeInTheDocument();
});

test("early warning API errors use a stable user-facing message", async () => {
  vi.mocked(api.getAlerts).mockRejectedValueOnce(new Error("backend traceback"));
  render(<MemoryRouter><AlertsPage /></MemoryRouter>);
  expect(await screen.findByText("Early-warning data could not be loaded.")).toBeInTheDocument();
});

test("API errors have a visible recovery state", async () => {
  vi.mocked(api.getProjects).mockRejectedValueOnce(new Error("Backend unavailable"));
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);
  expect(await screen.findByText("Unable to load this view")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
});
