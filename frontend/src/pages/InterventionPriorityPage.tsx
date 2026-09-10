import { 
  ArrowDown, 
  ArrowRight, 
  ArrowUp, 
  Gauge, 
  Search, 
  RotateCcw, 
  Target, 
  AlertCircle, 
  Clock, 
  Activity,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import type { PriorityRecord } from "../types";
import { percent } from "../utils/format";
import { displayValue } from "../utils/presentation";
import { triggerButtonFeedback } from "../utils/haptics";

const PAGE_SIZE = 25;

export function InterventionPriorityPage() {
  const state = useAsync(() => api.getPriorities(), []);
  const [level, setLevel] = useState("");
  const [trajectory, setTrajectory] = useState("");
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => (state.data || []).filter(item =>
    (!level || item.intervention_priority_level === level) &&
    (!trajectory || item.trajectory_status === trajectory) &&
    (!action || item.recommended_review_action === action) &&
    (!search || `${item.project_name} ${item.canonical_project_id}`.toLocaleLowerCase("en-IN").includes(search.toLocaleLowerCase("en-IN")))
  ), [state.data, level, trajectory, action, search]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function update(setter: (value: string) => void, value: string) { 
    setter(value); 
    setPage(1); 
  }

  function handleReset() {
    setLevel("");
    setTrajectory("");
    setAction("");
    setSearch("");
    setPage(1);
  }

  if (state.loading) return <LoadingState label="Building the national intervention queue…" />;
  if (state.error) return <ErrorState message="Intervention priorities could not be loaded." onRetry={state.retry} />;

  const allRecords = state.data || [];
  const criticalCount = allRecords.filter(item => item.intervention_priority_level === "CRITICAL").length;
  const immediateCount = allRecords.filter(item => item.recommended_review_action === "IMMEDIATE_REVIEW").length;
  const insufficientCount = allRecords.filter(item => item.trajectory_status === "INSUFFICIENT_HISTORY").length;

  return (
    <div className="page-stack command-center-page">
      <PageHeader 
        eyebrow="National Intervention Policy · Review Ranking" 
        title="Intervention Priority" 
        description="Ranks projects for official review using existing model risks, trajectory, alerts, peers, exposure, and schedule pressure. The score is not a probability." 
        actions={
          <>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.15)]">
              <Gauge size={13} />
              <span>INTERVENTION POLICY ACTIVE</span>
            </span>
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>LIVE TELEMETRY</span>
            </span>
          </>
        }
      />

      {/* Top 4 Telemetry KPI Cards */}
      <section className="priority-summary-grid grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Summary 
          label="Eligible projects" 
          value={allRecords.length} 
          icon={<Target size={16} className="text-cyan-400" />}
          sub="National monitored scope"
          color="var(--text-white)"
        />
        <Summary 
          label="Critical priority" 
          value={criticalCount} 
          icon={<AlertCircle size={16} style={{ color: "var(--rose)" }} />}
          sub="Score threshold ≥ 80 / 100"
          color="var(--rose)"
        />
        <Summary 
          label="Immediate review" 
          value={immediateCount} 
          icon={<Clock size={16} style={{ color: "var(--amber)" }} />}
          sub="Official action recommended"
          color="var(--amber)"
        />
        <Summary 
          label="Insufficient history" 
          value={insufficientCount} 
          icon={<Activity size={16} className="text-slate-400" />}
          sub="Baseline calibration pending"
          color="var(--text-secondary)"
        />
      </section>

      {/* Command Console Filter Panel */}
      <section className="panel priority-filter-panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md">
        <div className="flex items-center justify-between gap-3 mb-3 pb-2 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            <SlidersHorizontal size={14} className="text-cyan-400" />
            <span>QUEUE FILTER CONSOLE</span>
          </div>
          {(level || trajectory || action || search) && (
            <button
              type="button"
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                handleReset();
              }}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-cyan-500/40 transition-colors"
            >
              <RotateCcw size={12} />
              <span>RESET</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <label className="priority-search flex flex-col gap-1 text-xs font-mono uppercase tracking-wider text-[var(--text-secondary)]">
            <span>Project</span>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] focus-within:border-cyan-500/60 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all">
              <Search size={14} className="text-[var(--text-muted)] shrink-0" />
              <input 
                aria-label="Search priority projects" 
                value={search} 
                placeholder="Search name or ID..." 
                onChange={event => update(setSearch, event.target.value)} 
                className="w-full bg-transparent border-0 text-xs font-mono text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
              />
              {search && (
                <button 
                  type="button" 
                  onClick={() => update(setSearch, "")}
                  className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs font-mono"
                >
                  ✕
                </button>
              )}
            </div>
          </label>

          <Filter 
            label="Priority level" 
            value={level} 
            options={["CRITICAL", "HIGH", "MEDIUM", "LOW"]} 
            onChange={value => update(setLevel, value)} 
          />
          <Filter 
            label="Risk trend" 
            value={trajectory} 
            options={["ACCELERATING", "RAPIDLY_RISING", "RISING", "STABLE", "IMPROVING", "INSUFFICIENT_HISTORY"]} 
            onChange={value => update(setTrajectory, value)} 
          />
          <Filter 
            label="Recommended action" 
            value={action} 
            options={["IMMEDIATE_REVIEW", "EARLY_INTERVENTION", "VERIFY_DATA_URGENTLY", "ROUTINE_MONITORING"]} 
            onChange={value => update(setAction, value)} 
          />
        </div>
      </section>

      {/* Main Table Panel */}
      <section className="panel table-panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] overflow-hidden shadow-sm">
        <div className="panel-heading p-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)]">
          <div>
            <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">National queue</span>
            <h2 className="flex items-center gap-2 text-base font-bold text-[var(--text-primary)] mt-0.5">
              <Gauge size={19} className="text-cyan-400" />
              <span>Projects officials should review first</span>
            </h2>
          </div>
          <span className="quiet-note text-xs font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-3 py-1 rounded border border-[var(--border-subtle)]">
            {filtered.length.toLocaleString("en-IN")} matching projects · deterministic descending score
          </span>
        </div>

        {!rows.length ? (
          <EmptyState title="No projects match these filters" />
        ) : (
          <div className="table-scroll table-scroll-wrap overflow-x-auto">
            <table className="intervention-table w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/50 text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
                  <th className="py-3 px-3">Rank</th>
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-3">3-Month Risk</th>
                  <th className="py-3 px-3">6-Month Risk</th>
                  <th className="py-3 px-3">Trend</th>
                  <th className="py-3 px-3">Data Reliability</th>
                  <th className="py-3 px-3">Priority Score</th>
                  <th className="py-3 px-3">Priority Level</th>
                  <th className="py-3 px-3">Recommended Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]/60">
                {rows.map(item => (
                  <PriorityRow key={item.canonical_project_id} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Monospace Tactical Pagination */}
        <div className="pagination p-3 flex items-center justify-between border-t border-[var(--border-subtle)] bg-[var(--bg-card)]/30 text-xs font-mono">
          <span className="text-[var(--text-muted)]">
            Page {page} of {pageCount}
          </span>
          <div className="flex items-center gap-2">
            <button 
              aria-label="Previous page"
              disabled={page === 1} 
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                setPage(page - 1);
              }}
              className="inline-flex items-center gap-1 px-3 py-1 rounded bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-cyan-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft size={14} />
              <span>Previous</span>
            </button>
            <button 
              aria-label="Next page"
              disabled={page === pageCount} 
              onClick={(e) => {
                triggerButtonFeedback(e, "pop");
                setPage(page + 1);
              }}
              className="inline-flex items-center gap-1 px-3 py-1 rounded bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-cyan-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function PriorityRow({ item }: { item: PriorityRecord }) {
  const isTop3 = item.rank <= 3;
  const isCritical = item.intervention_priority_level === "CRITICAL";

  return (
    <tr className="hover:bg-[var(--bg-card)]/60 transition-colors">
      <td className="py-3 px-3">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center justify-center font-mono font-bold text-xs px-2 py-0.5 rounded ${
            isTop3 
              ? "bg-amber-500/15 text-amber-400 border border-amber-500/30" 
              : "bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-subtle)]"
          }`}>
            <strong>#{item.rank}</strong>
          </span>
        </div>
      </td>
      <td className="py-3 px-4 max-w-sm">
        <Link 
          className="project-link group block" 
          to={`/projects/${encodeURIComponent(item.canonical_project_id)}`}
        >
          <strong className="block font-medium text-[var(--text-primary)] group-hover:text-cyan-400 transition-colors leading-tight">
            {displayValue(item.project_name)}
          </strong>
          <span className="block font-mono text-[10px] text-cyan-400/80 group-hover:text-cyan-300 mt-0.5">
            {item.canonical_project_id}
          </span>
        </Link>
        <div className="flex flex-wrap items-center gap-1 mt-1 text-[11px] text-[var(--text-muted)]">
          <small>{displayValue(item.sector, "sector")} · {displayValue(item.state, "state")}</small>
        </div>
        <div className="mt-1 text-[10px] text-[var(--text-muted)] line-clamp-2">
          <small>{item.key_reason}</small>
        </div>
      </td>
      <td className="py-3 px-3 font-mono font-semibold">
        <span className={item.delay_probability_3m >= 0.5 ? "text-rose-400" : item.delay_probability_3m >= 0.25 ? "text-amber-400" : "text-emerald-400"}>
          {percent(item.delay_probability_3m)}
        </span>
      </td>
      <td className="py-3 px-3 font-mono text-[var(--text-secondary)]">
        {percent(item.delay_probability_6m)}
      </td>
      <td className="py-3 px-3">
        <div className="flex flex-col gap-0.5">
          <Trend status={item.trajectory_status} />
          <small className="font-mono text-[10px] text-[var(--text-muted)]">
            {item.risk_change_1m == null ? "No last-period value" : `${item.risk_change_1m >= 0 ? "+" : ""}${(item.risk_change_1m * 100).toFixed(1)} pp`}
          </small>
        </div>
      </td>
      <td className="py-3 px-3">
        <ReliabilityBadge score={item.data_reliability_score} />
      </td>
      <td className="py-3 px-3 font-mono">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <strong className="text-sm font-bold text-[var(--text-primary)]">
              {item.intervention_priority_score.toFixed(1)} / 100
            </strong>
          </div>
          {/* Visual Score Meter */}
          <div className="w-24 h-1.5 rounded-full bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-hidden">
            <div 
              className={`h-full rounded-full ${
                item.intervention_priority_score >= 80 
                  ? "bg-rose-500" 
                  : item.intervention_priority_score >= 60 
                    ? "bg-amber-500" 
                    : item.intervention_priority_score >= 40 
                      ? "bg-cyan-500" 
                      : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, Math.max(0, item.intervention_priority_score))}%` }}
            />
          </div>
          <small className="text-[9px] text-[var(--text-muted)]">Not a probability</small>
        </div>
      </td>
      <td className="py-3 px-3">
        <span className={`priority-level priority-${item.intervention_priority_level.toLowerCase()} inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${
          isCritical ? "border border-rose-500/40" : ""
        }`}>
          {isCritical && <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />}
          {displayLabel(item.intervention_priority_level)}
        </span>
      </td>
      <td className="py-3 px-3 font-mono text-xs">
        <strong className="text-[var(--text-primary)] font-semibold">
          {displayLabel(item.recommended_review_action)}
        </strong>
      </td>
    </tr>
  );
}

export function Trend({ status }: { status: PriorityRecord["trajectory_status"] }) {
  const improving = status === "IMPROVING";
  const stable = status === "STABLE" || status === "INSUFFICIENT_HISTORY";
  const Icon = improving ? ArrowDown : stable ? ArrowRight : ArrowUp;
  return (
    <span className={`trajectory-label trajectory-${status.toLowerCase().replaceAll("_", "-")} inline-flex items-center gap-1 text-[11px] font-mono font-medium`}>
      <Icon size={13} /> {displayLabel(status)}
    </span>
  );
}

function displayLabel(value: string) { 
  return value.replaceAll("_", " ").toLocaleLowerCase("en-IN").replace(/\b\w/g, letter => letter.toLocaleUpperCase("en-IN")); 
}

function Summary({ label, value, icon, sub, color }: { label: string; value: number; icon?: React.ReactNode; sub?: string; color?: string }) { 
  return (
    <article className="kpi-card-box">
      <div className="kpi-card-top">
        <span className="kpi-card-lbl" style={color ? { color } : undefined}>{label}</span>
        {icon}
      </div>
      <div className="kpi-card-num font-mono" style={color ? { color } : undefined}>
        <strong>{value.toLocaleString("en-IN")}</strong>
      </div>
      {sub && <div className="kpi-card-sub font-mono text-[10px]">{sub}</div>}
    </article>
  ); 
}

function Filter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) { 
  return (
    <label className="flex flex-col gap-1 text-xs font-mono uppercase tracking-wider text-[var(--text-secondary)]">
      <span>{label}</span>
      <select 
        value={value} 
        onChange={event => onChange(event.target.value)}
        className="px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-primary)] focus:border-cyan-500/60 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition-all cursor-pointer"
      >
        <option value="">All</option>
        {options.map(option => (
          <option value={option} key={option}>{displayLabel(option)}</option>
        ))}
      </select>
    </label>
  ); 
}

