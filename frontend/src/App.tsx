import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/StatePanel";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const ProjectExplorerPage = lazy(() => import("./pages/ProjectExplorerPage").then((module) => ({ default: module.ProjectExplorerPage })));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage").then((module) => ({ default: module.ProjectDetailPage })));
const AlertsPage = lazy(() => import("./pages/AlertsPage").then((module) => ({ default: module.AlertsPage })));
const PortfolioAnalyticsPage = lazy(() => import("./pages/PortfolioAnalyticsPage").then((module) => ({ default: module.PortfolioAnalyticsPage })));
const InterventionPriorityPage = lazy(() => import("./pages/InterventionPriorityPage").then((module) => ({ default: module.InterventionPriorityPage })));

export default function App() {
  return <Suspense fallback={<LoadingState label="Loading workspace…" />}><Routes><Route element={<Layout />}><Route index element={<DashboardPage />} /><Route path="projects" element={<ProjectExplorerPage />} /><Route path="projects/:projectId" element={<ProjectDetailPage />} /><Route path="alerts" element={<AlertsPage />} /><Route path="priorities" element={<InterventionPriorityPage />} /><Route path="analytics" element={<PortfolioAnalyticsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes></Suspense>;
}
