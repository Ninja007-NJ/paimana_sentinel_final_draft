import { 
  AlertTriangle, 
  ArrowUpRight, 
  ShieldAlert, 
  Bell, 
  Activity, 
  Search, 
  Filter, 
  RotateCcw,
  TrendingUp,
  AlertCircle,
  Gauge
} from "lucide-react";
import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { RiskBadge } from "../components/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import { month, percent } from "../utils/format";
import { alertTypeLabel, displayValue } from "../utils/presentation";
import { triggerButtonFeedback } from "../utils/haptics";

export function AlertsPage() {
  const state = useAsync(() => api.getAlerts(), []);
  const [severity, setSeverity] = useState("");
  const [alertType, setAlertType] = useState("");
  const [search, setSearch] = useState("");

  if (state.loading) return <LoadingState label="Building the early warning queue…" />;
  if (state.error) return <ErrorState message="Early-warning data could not be loaded." onRetry={state.retry} />;

  const source = state.data || [];
  const alertTypes = [...new Set(source.map(item => item.alert_type))].sort();

  const alerts = source.filter(item => {
    const matchesSeverity = !severity || item.severity === severity;
    const matchesType = !alertType || item.alert_type === alertType;
    const matchesSearch = !search || 
      `${item.project_name} ${item.canonical_project_id}`.toLowerCase().includes(search.toLowerCase());
    return matchesSeverity && matchesType && matchesSearch;
  });

  // Telemetry KPIs
  const criticalCount = source.filter(a => a.severity === "CRITICAL").length;
  const highRiskImpact = source.filter(a => (a.current_risk || 0) >= 0.5).length;
  const risingSpikeCount = source.filter(a => (a.recent_risk_change || 0) > 0).length;

  return (
    <div className="page-stack command-center-page">
      <PageHeader 
        eyebrow="Portfolio triage" 
        title="Early Warning Centre" 
        description="Deterministic monitoring signals layered on the frozen 3-month delay-risk model. Alerts prioritize review; they do not change the model prediction or establish causality." 
        actions={
          <>
            <Link 
              to="/priorities" 
              className="page-header-policy-btn"
              title="Navigate to Intervention Policy"
            >
              <Gauge size={13} />
              <span>Intervention Policy</span>
            </Link>
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>LIVE TELEMETRY</span>
            </span>
          </>
        }
      />

      {/* Top Telemetry KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 1. TOTAL ALERTS */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">TOTAL ACTIVE ALERTS</span>
            <Bell size={15} className="text-cyan-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {source.length.toLocaleString("en-IN")}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Queue length</div>
        </div>

        {/* 2. CRITICAL SEVERITY */}
        <div className="kpi-card-box kpi-card-critical">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl" style={{ color: "var(--rose)" }}>CRITICAL SEVERITY</span>
            <AlertCircle size={15} style={{ color: "var(--rose)" }} />
          </div>
          <div className="kpi-card-num font-mono" style={{ color: "var(--rose)" }}>
            {criticalCount}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Requires urgent review</div>
        </div>

        {/* 3. HIGH RISK IMPACT */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl" style={{ color: "var(--amber)" }}>HIGH RISK IMPACT</span>
            <AlertTriangle size={15} style={{ color: "var(--amber)" }} />
          </div>
          <div className="kpi-card-num font-mono" style={{ color: "var(--amber)" }}>
            {highRiskImpact}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Projects with risk ≥ 50%</div>
        </div>

        {/* 4. RECENT RISK SPIKES */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">RECENT RISK SPIKES</span>
            <TrendingUp size={15} className="text-rose-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {risingSpikeCount}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Positive delta in 1-mo horizon</div>
        </div>
      </div>

      {/* Notice Banner */}
      <div className="notice flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-card)] border border-amber-500/20 text-xs text-[var(--text-slate)]">
        <ShieldAlert size={16} className="text-amber-400 flex-shrink-0" />
        <span>Alerts prioritize review; they do not change the model prediction or establish causality.</span>
      </div>

      {/* Tactical Filter Bar */}
      <section className="panel filter-bar p-3.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-card)]" aria-label="Alert filters">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          {/* Quick Search */}
          <label className="flex flex-col gap-1 text-xs text-[var(--text-slate)] font-mono">
            <span className="uppercase text-[10px] font-bold text-[var(--text-muted)]">Search Project</span>
            <div className="relative flex items-center">
              <Search size={14} className="absolute left-3 text-[var(--text-muted)] pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name or ID..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] text-xs text-[var(--text-white)] font-mono focus:border-[var(--blue-brand)] focus:outline-none"
              />
            </div>
          </label>

          {/* Severity Dropdown */}
          <label className="flex flex-col gap-1 text-xs text-[var(--text-slate)] font-mono">
            <span className="uppercase text-[10px] font-bold text-[var(--text-muted)]">Severity</span>
            <select 
              aria-label="Severity"
              value={severity} 
              onChange={event => {
                triggerButtonFeedback(event, "pop");
                setSeverity(event.target.value);
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] text-xs text-[var(--text-white)] font-mono focus:border-[var(--blue-brand)] focus:outline-none"
            >
              <option value="">All severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>
          </label>

          {/* Alert Type Dropdown */}
          <label className="flex flex-col gap-1 text-xs text-[var(--text-slate)] font-mono">
            <span className="uppercase text-[10px] font-bold text-[var(--text-muted)]">Alert Type</span>
            <select 
              aria-label="Alert Type"
              value={alertType} 
              onChange={event => {
                triggerButtonFeedback(event, "pop");
                setAlertType(event.target.value);
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] text-xs text-[var(--text-white)] font-mono focus:border-[var(--blue-brand)] focus:outline-none"
            >
              <option value="">All alert types</option>
              {alertTypes.map(type => (
                <option key={type} value={type}>{alertTypeLabel(type)}</option>
              ))}
            </select>
          </label>

          {/* Reset Filters Action */}
          <div className="flex items-center">
            <button 
              className="secondary-button w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-mono font-semibold"
              onClick={(e) => { 
                triggerButtonFeedback(e, "pop");
                setSeverity(""); 
                setAlertType(""); 
                setSearch("");
              }}
            >
              <RotateCcw size={13} />
              <span>Clear filters</span>
            </button>
          </div>
        </div>
      </section>

      {/* Alert Queue Table */}
      {!alerts.length ? (
        <EmptyState title={source.length ? "No alerts match these filters" : "No active alerts"} />
      ) : (
        <section className="panel table-panel rounded-xl bg-[var(--bg-card)] border border-[var(--border-card)] overflow-hidden">
          <div className="panel-heading p-4 border-b border-[var(--border-card)] flex items-center justify-between">
            <div>
              <span className="eyebrow text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] block">Prioritized queue</span>
              <h2 className="text-base font-extrabold text-[var(--text-white)] font-sans m-0 flex items-center gap-2">
                <span>{alerts.length.toLocaleString("en-IN")} active alerts</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  SORTED BY RISK DELTA
                </span>
              </h2>
            </div>
          </div>

          <div className="table-scroll overflow-x-auto">
            <table className="w-full text-left text-xs font-sans">
              <thead>
                <tr className="border-b border-[var(--border-card)] bg-[var(--bg-card-inner)]/50 text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
                  <th className="py-3 px-4">Warning Priority</th>
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-4">Alert</th>
                  <th className="py-3 px-4">Current Risk</th>
                  <th className="py-3 px-4">Recent Change</th>
                  <th className="py-3 px-4">Data Reliability</th>
                  <th className="py-3 px-4">Intervention Priority</th>
                  <th className="py-3 px-4">Snapshot</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-card)]">
                {alerts.map((alert, index) => {
                  const isCrit = alert.severity === "CRITICAL";
                  return (
                    <tr 
                      key={alert.alert_id} 
                      className="hover:bg-[var(--bg-card-hover)] transition-colors group"
                    >
                      {/* Priority Rank */}
                      <td className="py-3 px-4 font-mono">
                        <div className="flex items-center gap-2">
                          <span className={`font-bold ${isCrit ? "text-rose-400" : "text-[var(--text-white)]"}`}>
                            #{String(index + 1).padStart(2, "0")}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold uppercase tracking-wide severity severity-${alert.severity.toLowerCase()} ${
                            isCrit 
                              ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" 
                              : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                          }`}>
                            {alert.severity}
                          </span>
                        </div>
                      </td>

                      {/* Project Name & Canonical ID */}
                      <td className="py-3 px-4">
                        <div className="flex flex-col">
                          <strong className="text-[var(--text-white)] group-hover:text-[var(--blue-brand)] transition-colors font-medium">
                            {displayValue(alert.project_name)}
                          </strong>
                          <span className="font-mono text-[10px] text-[var(--text-muted)] mt-0.5">
                            {alert.canonical_project_id}
                          </span>
                        </div>
                      </td>

                      {/* Alert Type & Explanation */}
                      <td className="py-3 px-4 max-w-xs">
                        <div className="flex flex-col">
                          <span className="alert-type flex items-center gap-1 font-semibold text-[var(--text-white)]">
                            <AlertTriangle size={13} className={isCrit ? "text-rose-400" : "text-amber-400"} />
                            {alertTypeLabel(alert.alert_type)}
                          </span>
                          <small className="text-[11px] text-[var(--text-slate)] mt-0.5 line-clamp-2">
                            {alert.explanation}
                          </small>
                        </div>
                      </td>

                      {/* Current Risk */}
                      <td className="py-3 px-4 font-mono">
                        <div className="flex flex-col gap-1">
                          <RiskBadge level={alert.current_risk >= 0.75 ? "CRITICAL" : alert.current_risk >= 0.5 ? "HIGH" : "MEDIUM"} />
                          <small className="font-bold text-[var(--text-white)]">
                            {percent(alert.current_risk)}
                          </small>
                        </div>
                      </td>

                      {/* Recent Change */}
                      <td className="py-3 px-4 font-mono">
                        {alert.recent_risk_change == null ? (
                          <span className="text-[var(--text-muted)]">—</span>
                        ) : (
                          <span className={`font-semibold flex items-center gap-0.5 ${
                            alert.recent_risk_change > 0 ? "text-rose-400" : "text-emerald-400"
                          }`}>
                            {alert.recent_risk_change > 0 ? "↑" : "↓"}
                            {`${alert.recent_risk_change >= 0 ? "+" : ""}${(alert.recent_risk_change * 100).toFixed(1)} pp`}
                          </span>
                        )}
                      </td>

                      {/* Data Reliability */}
                      <td className="py-3 px-4">
                        <ReliabilityBadge score={alert.data_reliability_score} />
                      </td>

                      {/* Intervention Priority */}
                      <td className="py-3 px-4 font-mono">
                        {alert.intervention_priority_score == null ? (
                          <span className="text-[var(--text-muted)]">—</span>
                        ) : (
                          <div className="flex flex-col">
                            <strong className="text-[var(--text-white)] font-bold">
                              {alert.intervention_priority_score.toFixed(1)} / 100
                            </strong>
                            <small className="text-[10px] text-[var(--text-muted)]">Review ranking</small>
                          </div>
                        )}
                      </td>

                      {/* Snapshot Month */}
                      <td className="py-3 px-4 font-mono text-[var(--text-slate)]">
                        {month(alert.latest_snapshot_month)}
                      </td>

                      {/* Action Link */}
                      <td className="py-3 px-4 text-right">
                        <Link 
                          className="icon-link inline-flex items-center justify-center p-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] hover:border-[var(--blue-brand)] text-[var(--text-slate)] hover:text-[var(--blue-brand)] transition-colors"
                          to={`/projects/${encodeURIComponent(alert.canonical_project_id)}`} 
                          aria-label={`Open ${displayValue(alert.project_name)}`}
                          onClick={(e) => triggerButtonFeedback(e, "click")}
                        >
                          <ArrowUpRight size={15} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
