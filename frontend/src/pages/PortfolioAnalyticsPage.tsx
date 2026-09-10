import { 
  BarChart3, 
  Landmark, 
  MapPinned, 
  Shapes, 
  TrendingUp, 
  AlertTriangle, 
  ShieldAlert, 
  Flame, 
  Sparkles,
  Building2,
  MapPin,
  TrendingDown,
  Layers,
  Gauge
} from "lucide-react";
import { Link } from "react-router-dom";
import { 
  Bar, 
  BarChart, 
  CartesianGrid, 
  Cell, 
  Legend, 
  Line, 
  LineChart, 
  ResponsiveContainer, 
  Tooltip, 
  XAxis, 
  YAxis 
} from "recharts";
import { api } from "../api/client";
import { AssistantPanel } from "../components/AssistantPanel";
import { PageHeader } from "../components/PageHeader";
import { ErrorState, LoadingState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import type { GroupAnalytics } from "../types";
import { crore, percent } from "../utils/format";
import { displayValue } from "../utils/presentation";

export function PortfolioAnalyticsPage() {
  const portfolioState = useAsync(() => api.getPortfolioAnalytics(), []);
  const sectorsState = useAsync(() => api.getSectorAnalytics(), []);
  const ministriesState = useAsync(() => api.getMinistryAnalytics(), []);
  const statesState = useAsync(() => api.getStateAnalytics(), []);

  if (portfolioState.loading) return <LoadingState label="Aggregating portfolio intelligence…" />;
  if (portfolioState.error) return <ErrorState message="Portfolio analytics could not be loaded." onRetry={portfolioState.retry} />;

  const portfolio = portfolioState.data!;
  const ministries = ministriesState.data || [];

  return (
    <div className="page-stack command-center-page">
      <PageHeader 
        eyebrow="MoSPI portfolio view" 
        title="Portfolio Analytics" 
        description={`Macro-level governance telemetry and predictive aggregation. Comparisons include groups with at least ${portfolio.minimum_group_size} projects to avoid misleading small-sample rankings.`} 
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
              <span>PORTFOLIO TELEMETRY ACTIVE</span>
            </span>
          </>
        }
      />

      {/* Top 4 Macro Telemetry KPI Cards */}
      <section className="stat-grid grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">Monitored projects</span>
            <BarChart3 size={15} className="text-cyan-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {portfolio.summary.project_count.toLocaleString("en-IN")}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Latest project snapshots</div>
        </div>

        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">Average delay risk</span>
            <TrendingUp size={15} className="text-amber-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {percent(portfolio.summary.average_delay_risk)}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">Median {percent(portfolio.summary.median_delay_risk)}</div>
        </div>

        <div className="kpi-card-box kpi-card-critical">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl" style={{ color: "var(--rose)" }}>High / critical</span>
            <AlertTriangle size={15} style={{ color: "var(--rose)" }} />
          </div>
          <div className="kpi-card-num font-mono" style={{ color: "var(--rose)" }}>
            {portfolio.summary.high_risk_count.toLocaleString("en-IN")}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">
            {portfolio.summary.high_risk_percentage.toFixed(1)}% of portfolio · {portfolio.summary.active_alert_count} alerts
          </div>
        </div>

        <div className="kpi-card-box">
          <div className="kpi-card-top">
            <span className="kpi-card-lbl">Current portfolio cost</span>
            <Landmark size={15} className="text-emerald-400" />
          </div>
          <div className="kpi-card-num text-[var(--text-white)] font-mono">
            {crore(portfolio.summary.aggregate_current_cost_cr)}
          </div>
          <div className="kpi-card-sub font-mono text-[10px]">
            Expenditure {crore(portfolio.summary.aggregate_expenditure_cr)}
          </div>
        </div>
      </section>

      {/* AI Assistant Grounded Panel */}
      <AssistantPanel />

      {/* Dual Chart Section */}
      <section className="dashboard-grid grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Distribution Bar Chart */}
        <article className="panel chart-panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md">
          <div className="panel-heading pb-3 mb-2 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <div>
              <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Severity Breakdown</span>
              <h2 className="text-sm font-bold text-[var(--text-primary)] mt-0.5">Portfolio risk distribution</h2>
            </div>
            <span className="text-[11px] font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-2 py-0.5 rounded border border-[var(--border-subtle)]">
              4 Category Buckets
            </span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={portfolio.risk_distribution} margin={{ top: 15, right: 15, left: -10, bottom: 5 }}>
              <CartesianGrid stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="risk_level" 
                tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "monospace" }} 
                axisLine={{ stroke: "var(--border-subtle)" }}
                tickLine={false}
              />
              <YAxis 
                tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "monospace" }} 
                axisLine={{ stroke: "var(--border-subtle)" }}
                tickLine={false}
              />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="p-2.5 rounded-lg bg-[var(--bg-card)] border border-cyan-500/40 shadow-xl text-xs font-mono">
                        <div className="font-bold text-[var(--text-primary)] uppercase">{data.risk_level} Risk</div>
                        <div className="text-cyan-400 mt-1 font-semibold">{data.count.toLocaleString("en-IN")} projects</div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {portfolio.risk_distribution.map((entry) => {
                  const level = String(entry.risk_level).toUpperCase();
                  const color = level === "CRITICAL" ? "#f43f5e" : level === "HIGH" ? "#f59e0b" : level === "MEDIUM" ? "#0ea5e9" : "#10b981";
                  return <Cell key={level} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </article>

        {/* Portfolio Risk Trend Line Chart */}
        <article className="panel chart-panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md">
          <div className="panel-heading pb-3 mb-2 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <div>
              <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Temporal Trajectory</span>
              <h2 className="text-sm font-bold text-[var(--text-primary)] mt-0.5">Portfolio risk trend</h2>
            </div>
            <span className="text-[11px] font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-2 py-0.5 rounded border border-[var(--border-subtle)]">
              Historical Snapshots
            </span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart 
              data={portfolio.risk_trend.map(row => ({ ...row, riskPct: row.average_delay_risk * 100 }))}
              margin={{ top: 15, right: 15, left: -10, bottom: 5 }}
            >
              <CartesianGrid stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="snapshot_month" 
                tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} 
                axisLine={{ stroke: "var(--border-subtle)" }}
                tickLine={false}
              />
              <YAxis 
                yAxisId="risk" 
                unit="%" 
                tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} 
                axisLine={{ stroke: "var(--border-subtle)" }}
                tickLine={false}
              />
              <YAxis 
                yAxisId="count" 
                orientation="right" 
                tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} 
                axisLine={{ stroke: "var(--border-subtle)" }}
                tickLine={false}
              />
              <Tooltip 
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="p-2.5 rounded-lg bg-[var(--bg-card)] border border-cyan-500/40 shadow-xl text-xs font-mono space-y-1">
                        <div className="text-[var(--text-muted)] text-[10px] uppercase font-bold">{label}</div>
                        {payload.map((entry, idx) => (
                          <div key={idx} className="flex items-center justify-between gap-3 text-xs">
                            <span style={{ color: entry.color }}>{entry.name}:</span>
                            <span className="font-bold text-[var(--text-primary)]">
                              {entry.name === "Average risk" ? `${Number(entry.value).toFixed(1)}%` : Number(entry.value).toLocaleString("en-IN")}
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend 
                wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} 
              />
              <Line 
                yAxisId="risk" 
                type="monotone" 
                dataKey="riskPct" 
                name="Average risk" 
                stroke="#f43f5e" 
                strokeWidth={2.4} 
                dot={{ r: 3, fill: "#f43f5e" }} 
              />
              <Line 
                yAxisId="count" 
                type="monotone" 
                dataKey="high_or_critical_count" 
                name="High / critical projects" 
                stroke="#06b6d4" 
                strokeWidth={2} 
                dot={{ r: 3, fill: "#06b6d4" }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </article>
      </section>

      {/* Group Risk Comparisons */}
      <GroupResult title="Sector risk comparison" state={sectorsState} keyName="sector" />
      <GroupResult title="Ministry / Department comparison" state={ministriesState} keyName="ministry_department" />
      <GroupResult title="State comparison" state={statesState} keyName="state" />

      {/* Special Analytical Sub-Tables */}
      {!ministriesState.loading && !ministriesState.error && (
        <section className="dashboard-grid grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GroupTable 
            title="Fastest-worsening ministries" 
            badge="Risk Escalation"
            rows={[...ministries]
              .filter(row => row.risk_change_1m != null)
              .sort((a, b) => (b.risk_change_1m || 0) - (a.risk_change_1m || 0))
              .slice(0, 10)} 
            keyName="ministry_department" 
          />
          <GroupTable 
            title="Lowest reporting reliability" 
            badge="Telemetry Integrity"
            rows={[...ministries]
              .sort((a, b) => a.average_data_reliability - b.average_data_reliability)
              .slice(0, 10)} 
            keyName="ministry_department" 
          />
        </section>
      )}
    </div>
  );
}

function GroupResult({ 
  title, 
  state, 
  keyName 
}: { 
  title: string; 
  state: { data: GroupAnalytics[] | null; error: Error | null; loading: boolean; retry: () => void }; 
  keyName: "sector" | "ministry_department" | "state" 
}) {
  if (state.loading) {
    return (
      <section className="panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <LoadingState label={`Loading ${title.toLowerCase()}…`} />
      </section>
    );
  }
  if (state.error) {
    return (
      <section className="panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <ErrorState message={`${title} could not be loaded.`} onRetry={state.retry} />
      </section>
    );
  }
  return <GroupTable title={title} rows={state.data || []} keyName={keyName} />;
}

function GroupTable({ 
  title, 
  rows, 
  keyName,
  badge
}: { 
  title: string; 
  rows: GroupAnalytics[]; 
  keyName: "sector" | "ministry_department" | "state";
  badge?: string;
}) {
  const kind = keyName === "ministry_department" ? "ministry" : keyName;

  return (
    <section className="panel table-panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] overflow-hidden shadow-sm">
      <div className="panel-heading p-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)]">
        <div>
          {badge && <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-amber-400 font-bold">{badge}</span>}
          <h2 className="text-sm font-bold text-[var(--text-primary)] mt-0.5">{title}</h2>
        </div>
        <span className="quiet-note text-xs font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-3 py-1 rounded border border-[var(--border-subtle)]">
          Sample sizes shown; groups below the minimum are suppressed
        </span>
      </div>

      {!rows.length ? (
        <div className="state-panel p-8 text-center">
          <strong className="block text-sm font-bold text-[var(--text-primary)]">No reportable groups</strong>
          <span className="text-xs text-[var(--text-muted)] mt-1 block">No groups met the minimum sample size.</span>
        </div>
      ) : (
        <div className="table-scroll table-scroll-wrap overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/50 text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
                <th className="py-3 px-3">#</th>
                <th className="py-3 px-4">Group</th>
                <th className="py-3 px-3">Projects</th>
                <th className="py-3 px-3">Average / Median Risk</th>
                <th className="py-3 px-3">High / Critical</th>
                <th className="py-3 px-3">Rapidly Rising</th>
                <th className="py-3 px-3">Data Reliability</th>
                <th className="py-3 px-3 text-right">Current Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]/60 font-mono">
              {rows.slice(0, 30).map((row, idx) => {
                const avgRisk = row.average_delay_risk;
                const riskColor = avgRisk >= 0.5 ? "text-rose-400" : avgRisk >= 0.25 ? "text-amber-400" : "text-emerald-400";
                return (
                  <tr key={String(row[keyName] || `row-${idx}`)} className="hover:bg-[var(--bg-card)]/60 transition-colors">
                    <td className="py-2.5 px-3 text-[var(--text-muted)] text-[11px]">
                      {(idx + 1).toString().padStart(2, "0")}
                    </td>
                    <td className="py-2.5 px-4 font-sans font-medium text-[var(--text-primary)] max-w-xs">
                      <strong>{displayValue(row[keyName], kind)}</strong>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-[var(--text-secondary)]">
                      {row.project_count ?? 0}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-col gap-1">
                        <span className={`font-semibold ${riskColor}`}>
                          {percent(row.average_delay_risk)} / {percent(row.median_delay_risk)}
                        </span>
                        <div className="w-20 h-1 bg-[var(--bg-card)] rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              avgRisk >= 0.5 ? "bg-rose-500" : avgRisk >= 0.25 ? "bg-amber-500" : "bg-emerald-500"
                            }`} 
                            style={{ width: `${Math.min(100, Math.max(0, avgRisk * 100))}%` }} 
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] ${
                        row.high_risk_count > 0 ? "bg-rose-500/10 text-rose-400 font-semibold" : "text-[var(--text-muted)]"
                      }`}>
                        {row.high_risk_count ?? 0} ({Number.isFinite(row.high_risk_percentage) ? row.high_risk_percentage.toFixed(1) : "0.0"}%)
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-flex items-center gap-1 text-[11px] ${
                        (row.rapidly_rising_risk_count ?? 0) > 0 ? "text-amber-400 font-semibold" : "text-[var(--text-muted)]"
                      }`}>
                        {(row.rapidly_rising_risk_count ?? 0) > 0 && "↑ "}
                        {row.rapidly_rising_risk_count ?? 0}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                      <span className="font-semibold text-[var(--text-primary)]">
                        {Number.isFinite(row.average_data_reliability) ? row.average_data_reliability.toFixed(1) : "—"}
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)]"> / 100</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-[var(--text-primary)]">
                      {crore(row.aggregate_current_cost_cr)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

