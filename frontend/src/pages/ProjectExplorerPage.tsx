import { 
  ChevronLeft, 
  ChevronRight, 
  Filter, 
  Search, 
  TrendingDown, 
  TrendingUp,
  Building2,
  Layers,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Gauge
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { RiskBadge } from "../components/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import type { PortfolioRiskRow, ProjectDetail, ProjectListItem } from "../types";
import { month, percent } from "../utils/format";
import { displayValue } from "../utils/presentation";
import { reliabilityLevel } from "../utils/reliability";
import { triggerButtonFeedback } from "../utils/haptics";

const PAGE_SIZE = 15;

export function ProjectExplorerPage() {
  const [searchParams] = useSearchParams();
  const requestedState = searchParams.get("state")?.trim() || "";
  const projectsState = useAsync(() => api.getProjects(), []);
  const [portfolioRows, setPortfolioRows] = useState<PortfolioRiskRow[]>([]);
  const [details, setDetails] = useState<Record<string, ProjectDetail>>({});
  const [filters, setFilters] = useState({ name: "", sector: "", state: requestedState, ministry: "", risk: "", reliability: "" });
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!projectsState.data) return;
    api.hydratePortfolioRisk(projectsState.data, (_done, _total, rows) => setPortfolioRows(rows)).then(setPortfolioRows).catch(() => undefined);
  }, [projectsState.data]);

  useEffect(() => {
    setFilters(current => current.state === requestedState ? current : { ...current, state: requestedState });
  }, [requestedState]);

  const riskMap = useMemo(() => new Map(portfolioRows.map((row) => [row.canonical_project_id, row])), [portfolioRows]);
  const sectors = useMemo(() => unique(projectsState.data?.map((row) => row.sector) ?? []), [projectsState.data]);
  const states = useMemo(
    () => unique([...(projectsState.data?.map((row) => row.state) ?? []), requestedState || null]),
    [projectsState.data, requestedState],
  );
  const ministries = useMemo(() => unique(Object.values(details).map((row) => row.project_metadata.ministry_department ?? null)), [details]);

  const filtered = useMemo(() => (projectsState.data ?? []).filter((row) => {
    const detail = details[row.canonical_project_id];
    const risk = riskMap.get(row.canonical_project_id)?.risk_level;
    return (!filters.name || `${row.project_name} ${row.canonical_project_id}`.toLowerCase().includes(filters.name.toLowerCase()))
      && (!filters.sector || row.sector === filters.sector)
      && (!filters.state || row.state === filters.state)
      && (!filters.risk || risk === filters.risk)
      && (!filters.reliability || reliabilityLevel(riskMap.get(row.canonical_project_id)?.latest_quality_score) === filters.reliability)
      && (!filters.ministry || detail?.project_metadata.ministry_department === filters.ministry);
  }), [projectsState.data, details, riskMap, filters]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Telemetry KPIs
  const totalProjects = projectsState.data?.length ?? 0;
  const criticalCohort = useMemo(() => {
    return filtered.filter(row => riskMap.get(row.canonical_project_id)?.risk_level === "CRITICAL").length;
  }, [filtered, riskMap]);
  const highReliabilityCohort = useMemo(() => {
    return filtered.filter(row => (riskMap.get(row.canonical_project_id)?.latest_quality_score ?? 0) >= 80).length;
  }, [filtered, riskMap]);

  useEffect(() => {
    let active = true;
    Promise.all(visible.filter((row) => !details[row.canonical_project_id]).map(async (row) => [row.canonical_project_id, await api.getProject(row.canonical_project_id)] as const))
      .then((entries) => active && entries.length && setDetails((current) => ({ ...current, ...Object.fromEntries(entries) })))
      .catch(() => undefined);
    return () => { active = false; };
  }, [visible.map((row) => row.canonical_project_id).join("|")]);

  useEffect(() => { setPage(1); }, [filters]);

  if (projectsState.loading) return <LoadingState label="Loading Project Explorer…" />;
  if (projectsState.error) return <ErrorState message={projectsState.error.message} onRetry={projectsState.retry} />;

  return (
    <div className="page-stack command-center-page">
      <PageHeader 
        eyebrow="Project registry" 
        title="Project Explorer" 
        description="Search the frozen portfolio, inspect current risk, and open a full project monitoring record." 
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
        {/* 1. TOTAL PROJECTS */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">MONITORED REGISTRY</span>
            <Building2 size={15} className="text-cyan-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {totalProjects.toLocaleString("en-IN")}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">National portfolio</div>
        </div>

        {/* 2. MATCHING FILTER */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">ACTIVE SELECTION</span>
            <Layers size={15} className="text-[var(--blue-brand)]" />
          </div>
          <div className="kpi-card-num text-[var(--blue-brand)] font-mono">
            {filtered.length.toLocaleString("en-IN")}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Projects matched</div>
        </div>

        {/* 3. CRITICAL RISK */}
        <div className="kpi-card-box kpi-card-critical">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl" style={{ color: "var(--rose)" }}>CRITICAL RISK</span>
            <AlertTriangle size={15} style={{ color: "var(--rose)" }} />
          </div>
          <div className="kpi-card-num font-mono" style={{ color: "var(--rose)" }}>
            {criticalCohort}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Immediate action required</div>
        </div>

        {/* 4. HIGH RELIABILITY */}
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl" style={{ color: "var(--emerald)" }}>HIGH RELIABILITY</span>
            <ShieldCheck size={15} style={{ color: "var(--emerald)" }} />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {highReliabilityCohort}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Quality score ≥ 80</div>
        </div>
      </div>

      {/* Advanced Filter Panel */}
      <section className="filter-panel panel p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-card)]">
        <div className="filter-title flex items-center justify-between pb-3 mb-3 border-b border-[var(--border-card)]">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-[var(--blue-brand)]" />
            <strong className="text-sm font-extrabold text-[var(--text-white)] uppercase font-mono">
              Filters
            </strong>
          </div>
          <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            {filtered.length.toLocaleString("en-IN")} projects
          </span>
        </div>

        <div className="filter-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <label className="search-field flex flex-col gap-1 font-mono text-xs">
            <span className="text-[10px] uppercase font-bold text-[var(--text-muted)]">Project name or ID</span>
            <div className="relative flex items-center">
              <Search size={14} className="absolute left-3 text-[var(--text-muted)] pointer-events-none" />
              <input 
                value={filters.name} 
                onChange={(event) => setFilters({ ...filters, name: event.target.value })} 
                placeholder="Search projects" 
                className="filter-search-input w-full pl-9 pr-3 py-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] text-xs text-[var(--text-white)] font-mono focus:border-[var(--blue-brand)] focus:outline-none"
              />
            </div>
          </label>

          <FilterSelect label="Sector" value={filters.sector} options={sectors} displayKind="sector" onChange={(sector) => setFilters({ ...filters, sector })} />
          <FilterSelect label="State" value={filters.state} options={states} displayKind="state" onChange={(state) => setFilters({ ...filters, state })} />
          <FilterSelect label="Ministry / Department" value={filters.ministry} options={ministries} displayKind="ministry" onChange={(ministry) => setFilters({ ...filters, ministry })} placeholder="Loaded ministries / departments" />
          <FilterSelect label="Risk level" value={filters.risk} options={["LOW", "MEDIUM", "HIGH", "CRITICAL"]} onChange={(risk) => setFilters({ ...filters, risk })} />
          <FilterSelect label="Data reliability" value={filters.reliability} options={["HIGH", "MEDIUM", "LOW"]} onChange={(reliability) => setFilters({ ...filters, reliability })} />
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-3 pt-3 border-t border-[var(--border-card)]/60">
          <p className="filter-note text-[11px] text-[var(--text-muted)] font-mono m-0">
            Ministry values are populated from project details as rows load. Risk bands come from backend trajectory responses.
          </p>
          <button 
            className="secondary-button self-start sm:self-auto flex items-center gap-1.5 py-1 px-3 rounded-lg text-xs font-mono font-semibold"
            onClick={(e) => {
              triggerButtonFeedback(e, "pop");
              setFilters({ name: "", sector: "", state: "", ministry: "", risk: "", reliability: "" });
            }}
          >
            <RotateCcw size={12} />
            <span>Clear all</span>
          </button>
        </div>
      </section>

      {/* Projects Table Panel */}
      <section className="panel table-panel rounded-xl bg-[var(--bg-card)] border border-[var(--border-card)] overflow-hidden">
        {!visible.length ? (
          <EmptyState title="No projects match these filters">
            Clear one or more filters and try again.
          </EmptyState>
        ) : (
          <div className="table-scroll overflow-x-auto">
            <table className="project-table w-full text-left text-xs font-sans">
              <thead>
                <tr className="border-b border-[var(--border-card)] bg-[var(--bg-card-inner)]/50 text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-4">Sector / State</th>
                  <th className="py-3 px-4">Physical Progress</th>
                  <th className="py-3 px-4">Current Target</th>
                  <th className="py-3 px-4">3-Month Delay Risk</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4">Data Reliability</th>
                  <th className="py-3 px-4 text-right">Risk Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-card)]">
                {visible.map((row) => (
                  <ExplorerRow 
                    key={row.canonical_project_id} 
                    project={row} 
                    detail={details[row.canonical_project_id]} 
                    risk={riskMap.get(row.canonical_project_id)} 
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tactical Pagination Console */}
        <div className="pagination p-3.5 border-t border-[var(--border-card)] flex items-center justify-between bg-[var(--bg-card-inner)]/30 font-mono text-xs">
          <span className="text-[var(--text-slate)]">
            PAGE <strong className="text-[var(--text-white)]">{String(page).padStart(2, "0")}</strong> OF <strong className="text-[var(--text-white)]">{String(pageCount).padStart(2, "0")}</strong>
          </span>
          <div className="flex items-center gap-1.5">
            <button 
              disabled={page === 1} 
              onClick={(e) => {
                triggerButtonFeedback(e, "click");
                setPage((value) => value - 1);
              }} 
              aria-label="Previous page"
              className="p-1.5 rounded-lg border border-[var(--border-card)] bg-[var(--bg-card)] disabled:opacity-30 disabled:pointer-events-none hover:border-[var(--blue-brand)] text-[var(--text-white)] transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button 
              disabled={page === pageCount} 
              onClick={(e) => {
                triggerButtonFeedback(e, "click");
                setPage((value) => value + 1);
              }} 
              aria-label="Next page"
              className="p-1.5 rounded-lg border border-[var(--border-card)] bg-[var(--bg-card)] disabled:opacity-30 disabled:pointer-events-none hover:border-[var(--blue-brand)] text-[var(--text-white)] transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function ExplorerRow({ project, detail, risk }: { project: ProjectListItem; detail?: ProjectDetail; risk?: PortfolioRiskRow }) {
  const progressPct = detail?.latest_snapshot.physical_progress_pct;

  return (
    <tr className="hover:bg-[var(--bg-card-hover)] transition-colors group">
      {/* Project */}
      <td className="py-3 px-4">
        <Link 
          to={`/projects/${encodeURIComponent(project.canonical_project_id)}`} 
          className="project-link flex flex-col group-hover:text-[var(--blue-brand)] transition-colors"
          onClick={(e) => triggerButtonFeedback(e, "click")}
        >
          <strong className="text-[var(--text-white)] font-semibold text-xs leading-snug">
            {displayValue(project.project_name)}
          </strong>
          <span className="font-mono text-[10px] text-[var(--text-muted)] mt-0.5">
            {project.canonical_project_id}
          </span>
        </Link>
      </td>

      {/* Sector / State */}
      <td className="py-3 px-4">
        <div className="flex flex-col">
          <strong className="text-[var(--text-white)] font-medium text-xs">
            {displayValue(project.sector, "sector")}
          </strong>
          <span className="text-[11px] text-[var(--text-slate)] mt-0.5">
            {displayValue(project.state, "state")}
          </span>
        </div>
      </td>

      {/* Physical Progress */}
      <td className="py-3 px-4 font-mono">
        {detail ? (
          <div className="flex flex-col gap-1 w-28">
            <span className="font-bold text-[var(--text-white)]">
              {progressPct != null ? `${progressPct.toFixed(1)}%` : "-"}
            </span>
            {progressPct != null && (
              <div className="w-full bg-[var(--border-card)] h-1.5 rounded-full overflow-hidden">
                <div 
                  className="h-full rounded-full bg-emerald-400"
                  style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
                />
              </div>
            )}
          </div>
        ) : (
          <span className="skeleton-cell animate-pulse inline-block w-16 h-4 bg-[var(--border-card)] rounded" />
        )}
      </td>

      {/* Current Target */}
      <td className="py-3 px-4 font-mono text-[var(--text-slate)]">
        {detail ? month(detail.latest_snapshot.current_target_doc?.slice(0, 7)) : <span className="skeleton-cell animate-pulse inline-block w-14 h-4 bg-[var(--border-card)] rounded" />}
      </td>

      {/* 3-Month Delay Risk */}
      <td className="py-3 px-4 font-mono font-bold text-[var(--text-white)]">
        {percent(project.latest_risk_score)}
      </td>

      {/* Risk Level */}
      <td className="py-3 px-4">
        {risk ? <RiskBadge level={risk.risk_level} /> : <span className="quiet-note text-xs text-[var(--text-muted)]">Assessing…</span>}
      </td>

      {/* Data Reliability */}
      <td className="py-3 px-4">
        <ReliabilityBadge score={detail?.data_quality_score ?? risk?.latest_quality_score} />
      </td>

      {/* Risk Trend */}
      <td className="py-3 px-4 font-mono text-right">
        {risk?.risk_change == null ? (
          <span className="quiet-note text-[var(--text-muted)]">-</span>
        ) : risk.risk_change >= 0 ? (
          <span className="trend-up inline-flex items-center gap-0.5 text-rose-400 font-semibold">
            <TrendingUp size={14} /> +{(risk.risk_change * 100).toFixed(1)} pp
          </span>
        ) : (
          <span className="trend-down inline-flex items-center gap-0.5 text-emerald-400 font-semibold">
            <TrendingDown size={14} /> {(risk.risk_change * 100).toFixed(1)} pp
          </span>
        )}
      </td>
    </tr>
  );
}

function FilterSelect({ label, value, options, onChange, placeholder = "All", displayKind }: { label: string; value: string; options: string[]; onChange: (value: string) => void; placeholder?: string; displayKind?: "state" | "sector" | "ministry" }) {
  return (
    <label className="flex flex-col gap-1 font-mono text-xs text-[var(--text-slate)]">
      <span className="text-[10px] uppercase font-bold text-[var(--text-muted)]">{label}</span>
      <select 
        aria-label={label}
        value={value} 
        onChange={(event) => {
          triggerButtonFeedback(event, "pop");
          onChange(event.target.value);
        }}
        className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-card-inner)] border border-[var(--border-card)] text-xs text-[var(--text-white)] font-mono focus:border-[var(--blue-brand)] focus:outline-none"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {displayKind ? displayValue(option, displayKind) : option}
          </option>
        ))}
      </select>
    </label>
  );
}

function unique(values: (string | null | undefined)[]) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b));
}
