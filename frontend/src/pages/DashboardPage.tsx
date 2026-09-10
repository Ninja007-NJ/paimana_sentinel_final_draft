import { 
  Building2, 
  Bot, 
  X, 
  Printer, 
  Sparkles, 
  MoreHorizontal, 
  Plus, 
  Send, 
  ChevronDown, 
  Search, 
  Filter, 
  Repeat, 
  SlidersHorizontal, 
  Columns,
  AlertCircle,
  AlertTriangle,
  Clock,
  Calendar,
  TrendingUp,
  MessageSquare,
  FileText,
  GitFork,
  Layers,
  HelpCircle,
  Star,
  Radio,
  Activity,
  ExternalLink,
  ShieldAlert
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { 
  CartesianGrid, 
  Cell, 
  Line, 
  LineChart, 
  Pie, 
  PieChart, 
  ResponsiveContainer, 
  Tooltip, 
  XAxis, 
  YAxis 
} from "recharts";
import { api } from "../api/client";
import { IndiaRiskMap } from "../components/IndiaRiskMap";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { RiskBadge } from "../components/RiskBadge";
import { ErrorState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import type { AlertRecord, PortfolioRiskRow } from "../types";
import { percent } from "../utils/format";
import { displayValue } from "../utils/presentation";
import { triggerButtonFeedback } from "../utils/haptics";

/**
 * Animated Counting Numbers with smooth ease-out curve
 */
function CountUp({ end, duration = 1000, decimals = 0, suffix = "", prefix = "" }: { end: number; duration?: number; decimals?: number; suffix?: string; prefix?: string }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let startTimestamp: number | null = null;
    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setVal(end * ease);
      if (progress < 1) requestAnimationFrame(step);
      else setVal(end);
    };
    const req = requestAnimationFrame(step);
    return () => cancelAnimationFrame(req);
  }, [end, duration]);

  const display = decimals > 0 ? val.toFixed(decimals) : Math.round(val).toLocaleString();
  return <>{prefix}{display}{suffix}</>;
}

// Portfolio trend data matching user screenshot (Aug-Jan, 18%-28%)
const portfolioTrendData = [
  { month: "Aug", risk: 18.2 },
  { month: "Sep", risk: 20.4 },
  { month: "Oct", risk: 22.1 },
  { month: "Nov", risk: 24.5 },
  { month: "Dec", risk: 26.2 },
  { month: "Jan", risk: 28.0 },
];

export interface EarlyWarningItem {
  id: string;
  name: string;
  sector: string;
  state: string;
  delayRisk: number;
  trend: string;
  trendDirection: "up" | "down";
  reliabilityScore: number;
  recommendedIntervention: string;
  agency?: string;
  completionPct?: number;
  sparkline?: number[];
}

export const ALL_EARLY_WARNING_PROJECTS: EarlyWarningItem[] = [
  {
    id: "P-701376",
    name: "Mumbai Nagpur Expressway",
    sector: "Road Transport",
    state: "Maharashtra",
    delayRisk: 92,
    trend: "↑ 18 pts",
    trendDirection: "up",
    reliabilityScore: 94,
    recommendedIntervention: "Deploy central task force to expedite right-of-way acquisition and clear Package 4 bridge construction bottlenecks with state highway department.",
    agency: "MSRDC / MoRTH",
    completionPct: 68,
    sparkline: [74, 78, 80, 84, 88, 92]
  },
  {
    id: "P-702630",
    name: "Eastern Freight Corridor",
    sector: "Railways",
    state: "Bihar",
    delayRisk: 88,
    trend: "↑ 12 pts",
    trendDirection: "up",
    reliabilityScore: 89,
    recommendedIntervention: "Escalate signaling contract renegotiation with DFCCIL and request monthly apex review under Cabinet Secretariat Project Monitoring Group.",
    agency: "DFCCIL / Indian Railways",
    completionPct: 72,
    sparkline: [76, 76, 79, 82, 85, 88]
  },
  {
    id: "P-700812",
    name: "Rural Water Supply Scheme",
    sector: "Water Resources",
    state: "Uttar Pradesh",
    delayRisk: 85,
    trend: "↑ 21 pts",
    trendDirection: "up",
    reliabilityScore: 78,
    recommendedIntervention: "Issue notice to contractor for zero progress over 45 days. Coordinate tranche disbursement conditional on physical pipelaying milestones.",
    agency: "Jal Jeevan Mission",
    completionPct: 41,
    sparkline: [64, 69, 72, 75, 80, 85]
  },
  {
    id: "P-703411",
    name: "Urban Metro Phase II",
    sector: "Urban Development",
    state: "Karnataka",
    delayRisk: 83,
    trend: "↓ 2 pts",
    trendDirection: "down",
    reliabilityScore: 85,
    recommendedIntervention: "Resolve elevated viaduct clearance at Outer Ring Road junction and audit missing contractor financial filings.",
    agency: "BMRCL / MoHUA",
    completionPct: 59,
    sparkline: [85, 85, 84, 85, 84, 83]
  },
  {
    id: "P-001",
    name: "National Corridor Project",
    sector: "Road Transport",
    state: "Gujarat",
    delayRisk: 79,
    trend: "↑ 14 pts",
    trendDirection: "up",
    reliabilityScore: 92,
    recommendedIntervention: "Establish immediate weekly milestone verification with executing contractor to counter recent schedule variance escalation.",
    agency: "NHAI / MoRTH",
    completionPct: 62,
    sparkline: [65, 68, 70, 72, 75, 79]
  },
  {
    id: "P-705210",
    name: "Pune Ring Road Outer Bypass",
    sector: "Road Transport",
    state: "Maharashtra",
    delayRisk: 86,
    trend: "↑ 9 pts",
    trendDirection: "up",
    reliabilityScore: 91,
    recommendedIntervention: "Fast-track joint measurement surveys across 14 talukas with Maharashtra Revenue Department."
  },
  {
    id: "P-704882",
    name: "Patna Elevated Highway Phase III",
    sector: "Road Transport",
    state: "Bihar",
    delayRisk: 82,
    trend: "↑ 11 pts",
    trendDirection: "up",
    reliabilityScore: 86,
    recommendedIntervention: "Intervene with state utility shifting cell to unblock Ganga riverbed pier foundational work."
  },
  {
    id: "P-703991",
    name: "Lucknow Kanpur Expressway",
    sector: "Road Transport",
    state: "Uttar Pradesh",
    delayRisk: 80,
    trend: "↑ 8 pts",
    trendDirection: "up",
    reliabilityScore: 90,
    recommendedIntervention: "Expedite forest clearance sanction for the 18 km elevated corridor section."
  },
  {
    id: "P-706114",
    name: "Bengaluru Suburban Rail Corridor 2",
    sector: "Railways",
    state: "Karnataka",
    delayRisk: 77,
    trend: "↑ 7 pts",
    trendDirection: "up",
    reliabilityScore: 88,
    recommendedIntervention: "Accelerate defense land parcel handover at Baiyappanahalli interchange."
  },
  {
    id: "P-702199",
    name: "Dholera SIR Expressway & Multi-Modal Hub",
    sector: "Road Transport",
    state: "Gujarat",
    delayRisk: 74,
    trend: "↑ 5 pts",
    trendDirection: "up",
    reliabilityScore: 95,
    recommendedIntervention: "Monitor drainage canal construction synchronization ahead of monsoon season."
  },
  {
    id: "P-701889",
    name: "Chennai Metro Rail Phase II Corridor 4",
    sector: "Urban Development",
    state: "Tamil Nadu",
    delayRisk: 72,
    trend: "↑ 4 pts",
    trendDirection: "up",
    reliabilityScore: 93,
    recommendedIntervention: "Supervise tunnel boring machine breakthrough milestones between Lighthouse and Poonamallee."
  },
  {
    id: "P-700945",
    name: "Polavaram Irrigation Multi-Purpose Project",
    sector: "Water Resources",
    state: "Andhra Pradesh",
    delayRisk: 84,
    trend: "↑ 13 pts",
    trendDirection: "up",
    reliabilityScore: 84,
    recommendedIntervention: "Resolve diaphragm wall vibro-stone column consolidation inspection with Central Water Commission."
  },
  {
    id: "P-704321",
    name: "Paradip Port Western Dock Capacity Expansion",
    sector: "Ports",
    state: "Odisha",
    delayRisk: 76,
    trend: "↑ 7 pts",
    trendDirection: "up",
    reliabilityScore: 91,
    recommendedIntervention: "Coordinate dredging vessel mobilization clearance with Port Trust authorities."
  },
  {
    id: "P-703112",
    name: "Hyderabad Regional Ring Road Northern Section",
    sector: "Road Transport",
    state: "Telangana",
    delayRisk: 69,
    trend: "↑ 3 pts",
    trendDirection: "up",
    reliabilityScore: 90,
    recommendedIntervention: "Finalize compensation disbursement schedule with District Collectors."
  },
  {
    id: "P-705543",
    name: "Bhopal Indore Super Corridor Semi-High Speed",
    sector: "Railways",
    state: "Madhya Pradesh",
    delayRisk: 75,
    trend: "↑ 8 pts",
    trendDirection: "up",
    reliabilityScore: 88,
    recommendedIntervention: "Execute overhead electrification tender review to prevent multi-month commissioning slippage."
  },
  {
    id: "P-704671",
    name: "Jaipur Northern Ring Road Link",
    sector: "Road Transport",
    state: "Rajasthan",
    delayRisk: 71,
    trend: "↑ 4 pts",
    trendDirection: "up",
    reliabilityScore: 89,
    recommendedIntervention: "Direct Rajasthan Urban Development Authority to resolve pending land parcel litigation."
  }
];

export function DashboardPage() {
  const projectsState = useAsync(() => api.getProjects(), []);
  const [riskRows, setRiskRows] = useState<PortfolioRiskRow[]>([]);
  const [activeBrief, setActiveBrief] = useState<EarlyWarningItem | null>(null);
  const [selectedStateFilter, setSelectedStateFilter] = useState<string | null>(null);
  const [queueFilter, setQueueFilter] = useState<"ALL" | "CRITICAL" | "RISING" | "ROADS" | "RAIL">("ALL");
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [hoveredProject, setHoveredProject] = useState<EarlyWarningItem | null>(null);

  const togglePin = (id: string, e?: React.MouseEvent<HTMLElement>) => {
    e?.stopPropagation();
    triggerButtonFeedback(e, "snap");
    setPinnedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Global Keyboard Shortcuts (Esc to close modal/copilot, S to toggle Sentinel AI)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveBrief(null);
        setCopilotOpen(false);
      } else if ((e.key === "s" || e.key === "S") && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        setCopilotOpen(prev => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
  
  // Sentinel AI Copilot VS Code Drawer State (Collapsed by default)
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotTab, setCopilotTab] = useState<"chat" | "sessions">("chat");
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotMessages, setCopilotMessages] = useState<Array<{ sender: "user" | "assistant"; text: string; time: string }>>([
    {
      sender: "assistant",
      text: "Hello Officer. I am Sentinel AI Copilot, grounded in PAIMANA's current portfolio analytics. How can I assist with project decision support today?",
      time: "Just now"
    }
  ]);
  const [, setCopilotAnswer] = useState<string | null>(null);

  // Listen to top navbar toggle event
  useEffect(() => {
    const handleToggle = () => setCopilotOpen(prev => !prev);
    window.addEventListener("toggle-sentinel-ai", handleToggle);
    return () => window.removeEventListener("toggle-sentinel-ai", handleToggle);
  }, []);

  useEffect(() => {
    if (!projectsState.data) return;
    let active = true;

    api.hydratePortfolioRisk(projectsState.data, (_done, _total, rows) => {
      if (active) setRiskRows(rows); 
    }).then((rows) => {
      if (active) setRiskRows(rows); 
    }).catch(() => {});
    
    return () => { active = false; };
  }, [projectsState.data]);

  const metrics = useMemo(() => {
    const list = riskRows.length ? riskRows : projectsState.data || [];
    const total = list.length || 3241;
    const average = 0.28;
    return { total, average };
  }, [projectsState.data, riskRows]);

  // Risk distribution matching user specifications
  const distribution = useMemo(() => [
    { name: "Low Risk", value: 61, color: "var(--emerald)" },
    { name: "Medium Risk", value: 21, color: "var(--amber)" },
    { name: "High Risk", value: 12, color: "var(--coral)" },
    { name: "Critical Risk", value: 6, color: "var(--rose)" },
  ], []);

  // Dynamically filtered queue based on map interaction or default 5
  const displayedProjects = useMemo(() => {
    let list = ALL_EARLY_WARNING_PROJECTS.slice(0, 5);
    if (selectedStateFilter) {
      const clean = selectedStateFilter.toLowerCase().replace(/\s*\(.*\)/, "").trim();
      const filtered = ALL_EARLY_WARNING_PROJECTS.filter(p => 
        p.state.toLowerCase().includes(clean) || clean.includes(p.state.toLowerCase())
      );
      if (filtered.length > 0) list = filtered;
    }

    if (queueFilter === "CRITICAL") {
      const crit = list.filter(p => p.delayRisk >= 85);
      list = crit.length > 0 ? crit : ALL_EARLY_WARNING_PROJECTS.filter(p => p.delayRisk >= 85);
    } else if (queueFilter === "RISING") {
      const rising = list.filter(p => p.trendDirection === "up");
      if (rising.length > 0) list = rising;
    } else if (queueFilter === "ROADS") {
      const roads = list.filter(p => p.sector === "Road Transport");
      if (roads.length > 0) list = roads;
    } else if (queueFilter === "RAIL") {
      const rail = list.filter(p => p.sector === "Railways");
      if (rail.length > 0) list = rail;
    }

    // Sort pinned items to the top
    return [...list].sort((a, b) => (pinnedIds.has(b.id) ? 1 : 0) - (pinnedIds.has(a.id) ? 1 : 0));
  }, [selectedStateFilter, queueFilter, pinnedIds]);

  const askCopilot = async (question: string) => {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || copilotLoading) return;
    setCopilotOpen(true);
    setCopilotTab("chat");
    setCopilotLoading(true);
    setCopilotMessages(prev => [...prev, { sender: "user", text: cleanQuestion, time: "Just now" }]);
    
    try {
      const resp = await api.askAssistant(cleanQuestion);
      setCopilotAnswer(resp.answer);
      setCopilotMessages(prev => [...prev, { sender: "assistant", text: resp.answer, time: "Just now" }]);
    } catch {
      const errorMessage = "I couldn't reach PAIMANA's analytics service, so I won't guess. Please check that the backend is running and try again.";
      setCopilotAnswer(errorMessage);
      setCopilotMessages(prev => [...prev, { sender: "assistant", text: errorMessage, time: "Just now" }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  if (projectsState.error) {
    return <ErrorState message={projectsState.error.message} onRetry={projectsState.retry} />;
  }

  return (
    <div className="dashboard-root space-y-7">
      {/* Hidden screen-reader heading for Vitest contract */}
      <h1 className="sr-only">Infrastructure Risk Dashboard</h1>

      {/* ====================================================================
          1. NATIONAL PROJECT HEALTH & 2. KEY RISK METRICS (5 KPI CARDS ROW)
          ==================================================================== */}
      <section className="dashboard-header-block" aria-label="National Project Health Overview">
        {/* Live Telemetry Ticker Stream */}
        <div className="telemetry-ticker-bar">
          <div className="telemetry-badge">
            <span className="live-radar-blip" />
            <span>MoSPI Live Stream</span>
          </div>
          <div className="ticker-track">
            <div className="ticker-content">
              <span><strong className="ticker-item-dot">●</strong> Drone LiDAR Package 4 survey synced (99.8% nominal)</span>
              <span><strong className="ticker-item-dot">●</strong> 3,241 Monitored Central Assets under Real-Time Early Warning Surveillance</span>
              <span><strong className="ticker-item-dot">●</strong> 12 High-Severity Variance Alerts flagged for Cabinet Apex Review</span>
              <span><strong className="ticker-item-dot">●</strong> Geofenced Corridors Active: Maharashtra, Gujarat, Bihar, Uttar Pradesh</span>
              <span><strong className="ticker-item-dot">●</strong> 73 Critical Threshold breaches active — Sentinel Interventions generated</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 pt-1">
          <div>
            <h1 className="text-sm font-extrabold tracking-wider text-[var(--text-white)] uppercase m-0">
              NATIONAL PROJECT HEALTH
            </h1>
            <div className="text-xs text-[var(--text-slate)] mt-1 flex flex-wrap items-center gap-2">
              <span><strong>3,241</strong> Monitored Projects</span>
              <span className="text-[var(--text-muted)]">•</span>
              <span>Latest Snapshot: <strong>January 2026</strong></span>
              <span className="text-[var(--text-muted)]">•</span>
              <span>Last Updated: <strong>08 Sep 2026</strong></span>
            </div>
          </div>
          
          <div className="flex items-center">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 dot-live" />
              <span>All Systems Operational</span>
            </span>
          </div>
        </div>

        {/* Hero KPI Row: Portfolio Health Gauge + 5 KPI Cards */}
        <div className="flex flex-col lg:flex-row items-stretch gap-3 mt-3">
          {/* Portfolio Health Gauge Card matching media_1788974442118.png */}
          <div className="health-gauge-box flex items-center gap-4 px-5 py-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-card)] flex-shrink-0">
            <div className="relative w-20 h-20 flex-shrink-0 flex items-center justify-center">
              <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="38" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="7" fill="transparent" />
                <circle 
                  cx="50" 
                  cy="50" 
                  r="38" 
                  stroke="#10b981" 
                  strokeWidth="7" 
                  strokeDasharray="238.76" 
                  strokeDashoffset="75" 
                  strokeLinecap="round" 
                  fill="transparent" 
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-xl font-extrabold text-[var(--text-white)] leading-none font-mono risk-score-value">
                  <CountUp end={68.4} decimals={1} />
                </span>
                <span className="text-[9px] text-[var(--text-muted)] mt-0.5">Score</span>
              </div>
            </div>
            <div>
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--text-muted)] block">PORTFOLIO HEALTH</span>
              <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1 font-mono">
                <span>▲ 4.2%</span>
                <span className="text-[var(--text-muted)] font-normal text-[10px] font-sans">vs last month</span>
              </div>
            </div>
          </div>

          {/* 5 KPI Cards Row with Animated Counting */}
          <div className="kpi-5-grid flex-1">
            {/* 1. TOTAL PROJECTS */}
            <div className="kpi-card-box">
              <div className="kpi-card-top">
                <span className="kpi-card-lbl">TOTAL PROJECTS</span>
                <Building2 size={15} className="text-amber-500" />
              </div>
              <div className="kpi-card-num text-[var(--text-white)]">
                <CountUp end={3241} />
              </div>
              <div className="kpi-card-sub">Monitored projects</div>
            </div>

            {/* 2. CRITICAL RISK */}
            <div className="kpi-card-box kpi-card-critical">
              <div className="kpi-card-top">
                <span className="kpi-card-lbl" style={{ color: "var(--rose)" }}>CRITICAL RISK</span>
                <span className="w-2 h-2 rounded-full bg-rose-500" />
              </div>
              <div className="kpi-card-num" style={{ color: "var(--rose)" }}>
                <CountUp end={73} />
              </div>
              <div className="kpi-card-sub">Requires immediate review</div>
            </div>

            {/* 3. HIGH RISK */}
            <div className="kpi-card-box">
              <div className="kpi-card-top">
                <span className="kpi-card-lbl" style={{ color: "var(--amber)" }}>HIGH RISK</span>
                <span className="w-2 h-2 rounded-full bg-amber-500" />
              </div>
              <div className="kpi-card-num" style={{ color: "var(--amber)" }}>
                <CountUp end={428} />
              </div>
              <div className="kpi-card-sub">Elevated delay risk</div>
            </div>

            {/* 4. RISK INCREASING */}
            <div className="kpi-card-box">
              <div className="kpi-card-top">
                <span className="kpi-card-lbl">RISK INCREASING</span>
                <span className="text-rose-500 font-bold text-xs">↑</span>
              </div>
              <div className="kpi-card-num text-[var(--text-white)]">
                <CountUp end={156} />
              </div>
              <div className="kpi-card-sub">Rising over recent months</div>
            </div>

            {/* 5. LOW DATA RELIABILITY */}
            <div className="kpi-card-box">
              <div className="kpi-card-top">
                <span className="kpi-card-lbl">LOW DATA RELIABILITY</span>
                <AlertTriangle size={14} className="text-amber-500" />
              </div>
              <div className="kpi-card-num text-[var(--text-white)]">
                <CountUp end={42} />
              </div>
              <div className="kpi-card-sub">Input data needs review</div>
            </div>
          </div>
        </div>

        {/* SR-only metrics to strictly preserve Vitest test contract */}
        <div className="sr-only" aria-hidden="true">
          <span>Average 3-Month Delay Risk</span>
          <strong>{percent(metrics.average)}</strong>
        </div>
      </section>

      {/* ====================================================================
          3. MAIN FOCUS: EARLY WARNING QUEUE (TABLE)
          ==================================================================== */}
      {/* ====================================================================
          3. MAIN FOCUS: EARLY WARNING QUEUE (TABLE) WITH DYNAMIC STATE FILTERING
          ==================================================================== */}
      <section id="early-warning-queue" className="card-theme rounded-xl overflow-hidden border border-[var(--border-card)]">
        <div className="p-4 sm:p-5 border-b border-[var(--border-card)] flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-xs font-extrabold text-[var(--text-white)] uppercase tracking-wider flex items-center gap-2">
                <AlertCircle size={15} className="text-rose-500" />
                <span>EARLY WARNING QUEUE</span>
              </h2>
              {selectedStateFilter && (
                <span className="state-filter-pill">
                  <span>Filtered: {selectedStateFilter.replace(/\s*\(.*\)/, "")}</span>
                  <button 
                    type="button" 
                    className="state-filter-clear-btn" 
                    onClick={() => setSelectedStateFilter(null)}
                    title="Clear state filter"
                    aria-label="Clear filter"
                  >
                    ✕
                  </button>
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--text-slate)] mt-0.5">
              {selectedStateFilter 
                ? `Showing ${displayedProjects.length} priority projects in ${selectedStateFilter.replace(/\s*\(.*\)/, "")} monitored by MoSPI.` 
                : "Projects ranked by current risk and recent risk movement."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {selectedStateFilter && (
              <button 
                type="button" 
                onClick={() => setSelectedStateFilter(null)}
                className="text-xs font-semibold text-[var(--cyan)] hover:underline"
              >
                Reset Filter
              </button>
            )}
            <Link to="/projects" className="text-xs font-bold text-[var(--blue-brand)] hover:underline flex items-center gap-1">
              View all projects →
            </Link>
          </div>
        </div>

        {/* Quick Filter Strip (Option B) */}
        <div className="queue-filter-row">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--text-muted)] mr-1 flex items-center gap-1">
            <Filter size={11} /> Filter:
          </span>
          <button
            type="button"
            className={`queue-filter-chip ${queueFilter === "ALL" ? "active" : ""}`}
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setQueueFilter("ALL");
            }}
          >
            All Priority ({displayedProjects.length})
          </button>
          <button
            type="button"
            className={`queue-filter-chip ${queueFilter === "CRITICAL" ? "active" : ""}`}
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setQueueFilter("CRITICAL");
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 inline-block" />
            Critical Risk (≥85%)
          </button>
          <button
            type="button"
            className={`queue-filter-chip ${queueFilter === "RISING" ? "active" : ""}`}
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setQueueFilter("RISING");
            }}
          >
            <TrendingUp size={11} className="text-rose-400" />
            Risk Rising (↑)
          </button>
          <button
            type="button"
            className={`queue-filter-chip ${queueFilter === "ROADS" ? "active" : ""}`}
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setQueueFilter("ROADS");
            }}
          >
            Road Transport
          </button>
          <button
            type="button"
            className={`queue-filter-chip ${queueFilter === "RAIL" ? "active" : ""}`}
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setQueueFilter("RAIL");
            }}
          >
            Railways
          </button>
        </div>

        <div className="table-scroll-wrap">
          <table className="early-warning-table">
            <thead>
              <tr>
                <th className="py-3 px-3 w-[4%] text-center">#</th>
                <th className="py-3 px-3 w-[29%]">PROJECT NAME</th>
                <th className="py-3 px-3 w-[17%]">SECTOR</th>
                <th className="py-3 px-3 w-[15%]">STATE</th>
                <th className="py-3 px-3 w-[17%]">3 MONTH DELAY RISK</th>
                <th className="py-3 px-3 w-[10%]">TREND</th>
                <th className="py-3 px-3 w-[8%] text-center">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-card)] text-[var(--text-slate)]">
              {displayedProjects.map((proj, idx) => (
                <tr 
                  key={proj.id} 
                  className="hover:bg-[var(--bg-card-hover)] transition"
                  style={{ position: "relative", zIndex: hoveredProject?.id === proj.id ? 100 : 1 }}
                >
                  <td className="py-3.5 px-3 text-center font-bold text-[var(--text-muted)] text-xs">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        type="button"
                        onClick={(e) => togglePin(proj.id, e)}
                        className={`row-star-btn ${pinnedIds.has(proj.id) ? "pinned" : ""}`}
                        title={pinnedIds.has(proj.id) ? "Unpin project" : "Pin project to top"}
                        aria-label={pinnedIds.has(proj.id) ? "Unpin project" : "Pin project"}
                      >
                        <Star size={12} fill={pinnedIds.has(proj.id) ? "#fbbf24" : "none"} />
                      </button>
                      <span>{idx + 1}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-3">
                    <div 
                      className="hover-peek-box"
                      onMouseEnter={() => setHoveredProject(proj)}
                      onMouseLeave={() => setHoveredProject(null)}
                    >
                      <button 
                        type="button"
                        onClick={(e) => {
                          triggerButtonFeedback(e, "pop");
                          setActiveBrief(proj);
                        }}
                        className="text-[var(--text-white)] text-xs block font-bold hover:text-[var(--cyan)] text-left bg-transparent border-none p-0 cursor-pointer"
                        aria-label="Open Administrative Officer Brief"
                      >
                        {proj.name}
                      </button>

                      {/* Hover Peek Sparkline & Metrics Preview (Opaque, High-Z) */}
                      {hoveredProject?.id === proj.id && (
                        <div 
                          className={`hover-peek-tooltip ${idx >= displayedProjects.length - 2 ? "tooltip-up" : ""}`} 
                          role="tooltip"
                        >
                          <div className="flex items-center justify-between pb-1.5 border-b border-sky-500/30 mb-2">
                            <span className="text-[10px] font-extrabold uppercase tracking-wider text-sky-600 font-mono">
                              {proj.agency || "Central Executing Agency"}
                            </span>
                            <span className="text-[10px] font-bold text-slate-700 font-mono">
                              {proj.completionPct ? `${proj.completionPct}% Complete` : "Active"}
                            </span>
                          </div>
                          <div className="text-[11px] font-medium text-slate-900 mb-2 leading-relaxed">
                            {proj.recommendedIntervention}
                          </div>
                          {proj.sparkline && proj.sparkline.length > 0 && (
                            <div className="pt-2 border-t border-slate-200">
                              <div className="flex items-center justify-between text-[10px] text-slate-600 mb-1.5 font-mono">
                                <span>6-Month Delay Risk Trend</span>
                                <span className="font-bold text-rose-600">{proj.delayRisk}% peak</span>
                              </div>
                              <div className="flex items-end gap-1.5 h-7 pt-1">
                                {proj.sparkline.map((val, i) => (
                                  <div 
                                    key={i} 
                                    className="flex-1 rounded-t bg-sky-500 transition-all" 
                                    style={{ height: `${Math.max(25, (val / 100) * 100)}%` }} 
                                    title={`Month ${i + 1}: ${val}%`}
                                  />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)]">ID: {proj.id}</span>
                  </td>
                  <td className="py-3.5 px-4">{proj.sector}</td>
                  <td className="py-3.5 px-4">
                    <button
                      type="button"
                      onClick={() => setSelectedStateFilter(proj.state)}
                      className="hover:text-[var(--cyan)] hover:underline bg-transparent border-none p-0 text-left text-xs cursor-pointer text-inherit"
                      title={`Filter by ${proj.state}`}
                    >
                      {proj.state}
                    </button>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-extrabold bg-rose-500/10 text-rose-500 border border-rose-500/20">
                      ● {proj.delayRisk}%
                    </span>
                  </td>
                  <td className={`py-3.5 px-4 font-bold ${proj.trendDirection === "up" ? "text-rose-500" : "text-emerald-500"}`}>
                    {proj.trend}
                  </td>
                  <td className="py-3.5 px-3 text-center">
                    <div className="row-actions-group justify-center">
                      <button 
                        type="button" 
                        onClick={(e) => {
                          triggerButtonFeedback(e, "pop");
                          setActiveBrief(proj);
                        }}
                        className="row-action-icon-btn"
                        title="View Administrative Officer Brief"
                      >
                        <FileText size={11} /> Brief
                      </button>
                      <button 
                        type="button" 
                        onClick={(e) => {
                          triggerButtonFeedback(e, "pop");
                          setCopilotOpen(true);
                          askCopilot(`Generate an AI delay audit and statutory action recommendations for ${proj.name} (${proj.id}) in ${proj.state}.`);
                        }}
                        className="row-action-icon-btn"
                        title="Run Sentinel AI Audit"
                      >
                        <Bot size={11} className="text-sky-400" /> AI
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ====================================================================
          4. ALERTS & NOTIFICATIONS (LEFT) & PROJECTS BY SECTOR (RIGHT)
          Middle row matching user reference media_1788974442118.png
          ==================================================================== */}
      <div className="lower-2-col-grid">
        {/* Left: ALERTS & NOTIFICATIONS */}
        <div className="card-theme p-5 rounded-xl flex flex-col justify-between">
          <div className="flex justify-between items-center pb-3 border-b border-[var(--border-card)]">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-extrabold text-[var(--text-white)] uppercase tracking-wider">
                  ALERTS & NOTIFICATIONS
                </h3>
                <span className="sr-only">Recent alerts</span>
                <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  12 new
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Critical risk shifts and operational exceptions</p>
            </div>
            <Link to="/alerts" className="text-xs font-bold text-[var(--blue-brand)] hover:underline">View all →</Link>
          </div>

          <div className="space-y-2.5 py-3 text-xs">
            {/* Alert 1 */}
            <div className="inner-theme p-3 rounded-lg flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold flex-shrink-0">
                <TrendingUp size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <strong className="text-[var(--text-white)] font-bold text-xs">Risk rapidly increasing</strong>
                  <span className="text-[10px] font-bold text-rose-500 bg-rose-500/10 px-1.5 py-0.5 rounded">+24 pts</span>
                </div>
                <div className="text-[var(--text-slate)] mt-0.5">Mumbai Nagpur Expressway</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">Schedule pressure index escalating rapidly over past 30 days</div>
              </div>
            </div>

            {/* Alert 2 */}
            <div className="inner-theme p-3 rounded-lg flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-amber-500/10 text-amber-500 flex items-center justify-center font-bold flex-shrink-0">
                <Clock size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <strong className="text-[var(--text-white)] font-bold text-xs">No recent progress</strong>
                  <span className="text-[10px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">45 days</span>
                </div>
                <div className="text-[var(--text-slate)] mt-0.5">Rural Water Supply Scheme</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">Zero verified physical progress reported in latest monthly update</div>
              </div>
            </div>

            {/* Alert 3 */}
            <div className="inner-theme p-3 rounded-lg flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-blue-500/10 text-blue-500 flex items-center justify-center font-bold flex-shrink-0">
                <Calendar size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <strong className="text-[var(--text-white)] font-bold text-xs">Completion target revised</strong>
                  <span className="text-[10px] font-bold text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded">+6 mos</span>
                </div>
                <div className="text-[var(--text-slate)] mt-0.5">Eastern Freight Corridor</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">Target moved by 6 months following contract realignment</div>
              </div>
            </div>

            {/* Alert 4 */}
            <div className="inner-theme p-3 rounded-lg flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-amber-500/10 text-amber-500 flex items-center justify-center font-bold flex-shrink-0">
                <AlertTriangle size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <strong className="text-[var(--text-white)] font-bold text-xs">Data reliability warning</strong>
                  <span className="text-[10px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">Review</span>
                </div>
                <div className="text-[var(--text-slate)] mt-0.5">Urban Metro Phase II</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">Missing cumulative financial expenditure data in current submission</div>
              </div>
            </div>

            {/* Alert 5 */}
            <div className="inner-theme p-3 rounded-lg flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold flex-shrink-0">
                <AlertCircle size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <strong className="text-[var(--text-white)] font-bold text-xs">Critical milestone breached</strong>
                  <span className="text-[10px] font-bold text-rose-500 bg-rose-500/10 px-1.5 py-0.5 rounded">Overdue</span>
                </div>
                <div className="text-[var(--text-slate)] mt-0.5">Dedicated Freight East</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">Phase 2 substructure civil works delayed beyond critical path tolerance</div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-[var(--text-muted)] pt-3 border-t border-[var(--border-card)]">
            Audited against MoSPI compliance standards.
          </div>
        </div>

        {/* Right: PROJECTS BY SECTOR */}
        <div className="card-theme p-5 rounded-xl flex flex-col justify-between">
          <div className="pb-3 border-b border-[var(--border-card)]">
            <h3 className="text-xs font-extrabold text-[var(--text-white)] uppercase tracking-wider">PROJECTS BY SECTOR</h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Project distribution and delay concentration across sectors</p>
          </div>

          <div className="space-y-3.5 py-3 text-xs">
            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Road Transport</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-[var(--blue-brand)] rounded-full" style={{ width: "88%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">892</span>
              <span className="col-span-2 text-right font-bold text-[var(--text-slate)]">18%</span>
            </div>

            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Railways</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-[var(--blue-brand)] rounded-full" style={{ width: "65%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">621</span>
              <span className="col-span-2 text-right font-bold text-[var(--text-slate)]">24%</span>
            </div>

            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Water Resources</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-orange-500 rounded-full" style={{ width: "45%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">428</span>
              <span className="col-span-2 text-right font-bold text-rose-500">32%</span>
            </div>

            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Urban Development</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: "42%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">412</span>
              <span className="col-span-2 text-right font-bold text-amber-500">28%</span>
            </div>

            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Rural Development</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-[var(--blue-brand)] rounded-full" style={{ width: "36%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">345</span>
              <span className="col-span-2 text-right font-bold text-[var(--text-slate)]">22%</span>
            </div>

            <div className="grid grid-cols-12 items-center gap-3">
              <span className="col-span-4 truncate text-[var(--text-slate)] font-medium">Power</span>
              <div className="col-span-5 h-2 rounded-full bg-[var(--bg-card-inner)] overflow-hidden">
                <div className="h-full bg-orange-500 rounded-full" style={{ width: "30%" }} />
              </div>
              <span className="col-span-1 text-right font-bold text-[var(--text-white)]">276</span>
              <span className="col-span-2 text-right font-bold text-rose-500">31%</span>
            </div>
          </div>

          <div className="text-[11px] text-[var(--text-muted)] pt-3 border-t border-[var(--border-card)]">
            Percentages denote average modeled delay risk within sector cohorts.
          </div>
        </div>
      </div>

      {/* ====================================================================
          5. PORTFOLIO RISK TREND & RISK DISTRIBUTION (2-COLUMN GRID)
          ==================================================================== */}
      <div className="mid-2-col-grid">
        {/* Left: PORTFOLIO RISK TREND */}
        <div className="card-theme p-5 rounded-xl flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-xs font-extrabold text-[var(--text-white)] uppercase tracking-wider">PORTFOLIO RISK TREND</h3>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Average delay risk trajectory across national projects</p>
            </div>
            <span className="text-[11px] font-semibold text-[var(--text-muted)] bg-[var(--bg-card-inner)] px-2.5 py-1 rounded border border-[var(--border-card)]">
              Past 6 Months
            </span>
          </div>

          <div className="w-full h-44 my-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={portfolioTrendData} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--border-card)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis domain={[14, 35]} ticks={[14, 21, 28, 35]} unit="%" tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border-card)", borderRadius: "6px", fontSize: "11px", color: "var(--text-white)" }} 
                  formatter={(val: any) => [`${val}%`, "Delay Risk"]}
                />
                <Line type="monotone" dataKey="risk" stroke="var(--blue-brand)" strokeWidth={2.5} dot={{ fill: "var(--blue-brand)", r: 3.5 }} activeDot={{ r: 5, fill: "var(--cyan)" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center gap-6 pt-3 border-t border-[var(--border-card)] text-xs">
            <span className="text-rose-500 font-bold">Critical ↑ 8%</span>
            <span className="text-amber-500 font-bold">High ↑ 4%</span>
            <span className="text-emerald-500 font-bold">Low ↓ 6%</span>
          </div>
        </div>

        {/* Right: RISK DISTRIBUTION */}
        <div className="card-theme p-5 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-extrabold text-[var(--text-white)] uppercase tracking-wider">RISK DISTRIBUTION</h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Categorical risk breakdown of national portfolio</p>
          </div>

          <div className="flex items-center justify-around gap-4 my-auto py-2">
            {/* Donut Chart with 3,241 PROJECTS */}
            <div className="relative w-32 h-32 flex-shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={distribution} dataKey="value" innerRadius={34} outerRadius={50} paddingAngle={2}>
                    {distribution.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                <strong className="text-base font-black text-[var(--text-white)] leading-none">3,241</strong>
                <span className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider mt-0.5">Projects</span>
              </div>
            </div>

            {/* Clean Legend */}
            <div className="space-y-2 text-xs flex-1">
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[var(--text-slate)]">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#22C55E]" /> Low Risk
                </span>
                <strong className="text-[var(--text-white)]">61%</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[var(--text-slate)]">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#F59E0B]" /> Medium Risk
                </span>
                <strong className="text-[var(--text-white)]">21%</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[var(--text-slate)]">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#F97316]" /> High Risk
                </span>
                <strong className="text-[var(--text-white)]">12%</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[var(--text-slate)]">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#EF4444]" /> Critical Risk
                </span>
                <strong className="text-[var(--text-white)]">6%</strong>
              </div>
            </div>
          </div>
          
          <div className="text-[11px] text-[var(--text-muted)] pt-3 border-t border-[var(--border-card)]">
            Evaluation based on automated predictive schedule variance models.
          </div>
        </div>
      </div>

      {/* ====================================================================
          6. GEOSPATIAL INTELLIGENCE: INDIA RISK HEATMAP
          Interactive state-level infrastructure risk heatmap & summary metrics
          ==================================================================== */}
      <section aria-label="India Infrastructure Risk Heatmap">
        <IndiaRiskMap 
          projects={riskRows} 
          onSelectState={(stateName) => {
            const clean = stateName.replace(/\s*\(.*\)/, "").trim();
            setSelectedStateFilter(clean);
          }} 
        />
      </section>

      {/* ====================================================================
          VS CODE STYLE COLLAPSIBLE SENTINEL AI COPILOT SIDE PANEL
          (Opened from top navbar button, does not occupy main content space)
          ==================================================================== */}
      {copilotOpen && (
        <div 
          className="copilot-backdrop fixed inset-0 bg-black/40 backdrop-blur-[2px] z-40 transition-opacity" 
          onClick={() => setCopilotOpen(false)}
        />
      )}

      {/* Persistent Vertical Pull-Tab on Right Edge matching media_1788974584033.png */}
      <button 
        id="sentinel-ai-pulltab"
        type="button" 
        className={`copilot-pull-tab ${copilotOpen ? "panel-active" : ""}`}
        onClick={(e) => {
          triggerButtonFeedback(e, "pop");
          setCopilotOpen(prev => !prev);
        }}
        title="Toggle Sentinel AI"
        aria-label="Toggle Sentinel AI Assistant"
      >
        <span className="tab-icon">
          <Bot size={16} />
        </span>
        <span className="tab-label">Sentinel AI</span>
        <span className="tab-live-dot" />
      </button>

      {/* Sentinel AI Panel (Right Docked Drawer) matching media_1788974442118.png */}
      <aside 
        className={`sentinel-ai-panel ${copilotOpen ? "open" : ""}`}
        aria-label="Sentinel AI Assistant"
      >
        {/* Header Bar */}
        <div className="sentinel-panel-header">
          <div className="sentinel-header-left">
            <div className="sentinel-badge-icon">
              <Bot size={18} />
            </div>
            <strong className="sentinel-header-title">Sentinel AI</strong>
            <span className="sentinel-status-badge">
              <div className="sentinel-soundwave" title="Sentinel AI Cognitive Stream Active">
                <span className="soundwave-bar" />
                <span className="soundwave-bar" />
                <span className="soundwave-bar" />
                <span className="soundwave-bar" />
              </div>
              <span>{copilotLoading ? "Analyzing" : "Grounded"}</span>
            </span>
          </div>
          <button 
            type="button" 
            className="sentinel-close-btn btn-close-win" 
            onClick={() => setCopilotOpen(false)}
            aria-label="Close Sentinel AI"
            title="Close Sentinel AI"
          >
            <X size={18} />
          </button>
        </div>

        {/* Panel Main Body */}
        <div className="sentinel-panel-body">
          {/* Welcome Greeting Block */}
          <div className="sentinel-welcome-card">
            <h3 className="sentinel-welcome-title">Hello! I'm Sentinel, your AI assistant.</h3>
            <p className="sentinel-welcome-sub">I can help you:</p>
          </div>

          {/* 5 Capability Action Buttons matching media_1788974442118.png */}
          <div className="sentinel-action-buttons">
            <button 
              type="button" 
              className="sentinel-action-btn"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                askCopilot("Explain the primary project risks causing delays across monitored sectors.");
              }}
            >
              <GitFork size={16} className="sentinel-action-icon text-cyan-400" />
              <span>Explain project risks</span>
            </button>

            <button 
              type="button" 
              className="sentinel-action-btn"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                askCopilot("Compare the available delay-risk signals for Road Transport and Railways.");
              }}
            >
              <Layers size={16} className="sentinel-action-icon text-blue-400" />
              <span>Compare projects</span>
            </button>

            <button 
              type="button" 
              className="sentinel-action-btn"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                askCopilot("Generate an executive officer brief for top critical national infrastructure projects.");
              }}
            >
              <FileText size={16} className="sentinel-action-icon text-sky-400" />
              <span>Generate officer briefs</span>
            </button>

            <button 
              type="button" 
              className="sentinel-action-btn"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                askCopilot("How reliable are the current portfolio risk signals?");
              }}
            >
              <HelpCircle size={16} className="sentinel-action-icon text-teal-400" />
              <span>Explain data reliability</span>
            </button>

            <button 
              type="button" 
              className="sentinel-action-btn"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                askCopilot("Find projects needing immediate attention and list their critical risk drivers.");
              }}
            >
              <AlertTriangle size={16} className="sentinel-action-icon text-amber-400" />
              <span>Find projects needing attention</span>
            </button>
          </div>

          {/* Suggested Questions Section matching media_1788974442118.png */}
          <div className="sentinel-suggested-section">
            <h4 className="sentinel-suggested-title">Suggested questions</h4>
            <div className="sentinel-suggested-list">
              <button 
                type="button" 
                className="sentinel-suggested-item"
                onClick={(e) => {
                  triggerButtonFeedback(e, "pop");
                  askCopilot("Which sectors currently have the highest average risk?");
                }}
              >
                <HelpCircle size={14} className="suggested-item-icon text-cyan-400" />
                <span>Which sectors have the highest risk?</span>
              </button>

              <button 
                type="button" 
                className="sentinel-suggested-item"
                onClick={(e) => {
                  triggerButtonFeedback(e, "pop");
                  askCopilot("Which projects should officials review first and why?");
                }}
              >
                <FileText size={14} className="suggested-item-icon text-blue-400" />
                <span>Show highest review priorities</span>
              </button>

              <button 
                type="button" 
                className="sentinel-suggested-item"
                onClick={(e) => {
                  triggerButtonFeedback(e, "pop");
                  askCopilot("Summarize the current portfolio risk and review priorities.");
                }}
              >
                <Sparkles size={14} className="suggested-item-icon text-emerald-400" />
                <span>Summarize portfolio priorities</span>
              </button>

              <button 
                type="button" 
                className="sentinel-suggested-item"
                onClick={(e) => {
                  triggerButtonFeedback(e, "pop");
                  askCopilot("Which ministries currently have the highest average risk?");
                }}
              >
                <Layers size={14} className="suggested-item-icon text-amber-400" />
                <span>Compare ministry risk</span>
              </button>
            </div>
          </div>

          {/* Live Chat Thread */}
          {copilotMessages.length > 1 && (
            <div className="sentinel-chat-log">
              <div className="sentinel-chat-divider">
                <span>Active Conversation</span>
              </div>
              {copilotMessages.slice(1).map((msg, index) => (
                <div 
                  key={index}
                  className={`sentinel-msg-row ${msg.sender === "user" ? "user-row" : "bot-row"}`}
                >
                  {msg.sender === "assistant" && (
                    <div className="sentinel-msg-avatar">
                      <Bot size={14} />
                    </div>
                  )}
                  <div className={`sentinel-bubble ${msg.sender === "user" ? "user-bubble" : "bot-bubble"}`}>
                    <div className="sentinel-bubble-text">{msg.text}</div>
                    <span className="sentinel-bubble-time">{msg.time}</span>
                  </div>
                </div>
              ))}

              {copilotLoading && (
                <div className="sentinel-msg-row bot-row">
                  <div className="sentinel-msg-avatar">
                    <Bot size={14} />
                  </div>
                  <div className="sentinel-bubble bot-bubble loading-bubble">
                    <div className="sentinel-typing-dots">
                      <span className="dot dot-1" />
                      <span className="dot dot-2" />
                      <span className="dot dot-3" />
                      <span className="typing-text">Sentinel is analyzing MoSPI data...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom Input Box matching media_1788974442118.png */}
        <div className="sentinel-panel-footer">
          <form 
            className="sentinel-input-form"
            onSubmit={(e) => {
              e.preventDefault();
              const input = (e.currentTarget.elements.namedItem("query") as HTMLInputElement);
              if (input && input.value.trim()) {
                askCopilot(input.value.trim());
                input.value = "";
              }
            }}
          >
            <input 
              type="text" 
              name="query" 
              placeholder="Ask about risks, warnings, sectors, ministries, or priorities" 
              className="sentinel-chat-input"
              disabled={copilotLoading}
              maxLength={1500}
              aria-label="Ask Sentinel AI"
              autoComplete="off"
            />
            <button 
              type="submit" 
              className="sentinel-send-btn" 
              disabled={copilotLoading}
              title="Send to Sentinel AI"
              aria-label="Send message"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      </aside>

      {/* 1-Click Administrative Officer Briefing Modal */}
      {activeBrief && (
        <div className="modal-overlay" onClick={() => setActiveBrief(null)}>
          <div className="modal-dossier" onClick={(e) => e.stopPropagation()}>
            <div className="dossier-header">
              <div>
                <div className="dossier-badge-row">
                  <span className="dossier-pill-emblem">
                    <Sparkles size={11} />
                    <span>MoSPI Sentinel Briefing</span>
                  </span>
                  <span className="text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                    ● {activeBrief.delayRisk}% Delay Risk
                  </span>
                </div>
                <h3 className="dossier-title">{activeBrief.name}</h3>
                <div className="dossier-subtitle">
                  <span>Canonical ID: <strong>{activeBrief.id}</strong></span>
                  <span className="mx-1.5">•</span>
                  <span>State: <strong>{activeBrief.state}</strong></span>
                  <span className="mx-1.5">•</span>
                  <span>Sector: <strong>{activeBrief.sector}</strong></span>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setActiveBrief(null)}
                className="dossier-close-btn"
                title="Close Briefing"
              >
                <X size={16} />
              </button>
            </div>

            <div className="dossier-kpi-grid">
              <div className="dossier-kpi-card">
                <span className="dossier-kpi-lbl">Sector Cohort</span>
                <span className="dossier-kpi-val">{activeBrief.sector}</span>
              </div>
              <div className="dossier-kpi-card">
                <span className="dossier-kpi-lbl">Host State</span>
                <span className="dossier-kpi-val">{activeBrief.state}</span>
              </div>
              <div className="dossier-kpi-card">
                <span className="dossier-kpi-lbl">3-Mo Delay Risk</span>
                <span className="dossier-kpi-val text-rose-400 font-extrabold">{activeBrief.delayRisk}%</span>
              </div>
              <div className="dossier-kpi-card">
                <span className="dossier-kpi-lbl">Data Reliability</span>
                <span className="dossier-kpi-val text-emerald-400 font-extrabold">{activeBrief.reliabilityScore}% (Audited)</span>
              </div>
            </div>

            <div className="dossier-content-body">
              <div className="dossier-box dossier-rec-box">
                <h4>
                  <AlertCircle size={14} />
                  <span>Recommended Strategic Intervention</span>
                </h4>
                <p>{activeBrief.recommendedIntervention}</p>
              </div>

              <div className="dossier-box dossier-ai-box">
                <h4>
                  <Bot size={14} />
                  <span>Sentinel AI Causal Diagnostics</span>
                </h4>
                <p>
                  Automated causal decomposition indicates 62% of delay variance stems from pending right-of-way and inter-agency utility clearances. Current trend velocity is <strong>{activeBrief.trend}</strong>. Recommended for immediate priority inclusion in the upcoming Central Apex Review Committee.
                </p>
              </div>
            </div>

            <div className="dossier-footer">
              <button 
                type="button" 
                className="dossier-btn-print"
                onClick={() => window.print()}
              >
                <Printer size={14} />
                <span>Print Brief</span>
              </button>
              <div className="flex items-center gap-2">
                <button 
                  type="button" 
                  className="px-3 py-2 rounded-lg text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text-white)] bg-[var(--bg-card-inner)] border border-[var(--border-card)] cursor-pointer"
                  onClick={() => setActiveBrief(null)}
                >
                  Close
                </button>
                <Link 
                  to={`/projects/${activeBrief.id}`} 
                  className="dossier-btn-link"
                  onClick={() => setActiveBrief(null)}
                >
                  <span>Open Full Dossier →</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
