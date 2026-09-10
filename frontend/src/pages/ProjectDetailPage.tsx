import { ArrowLeft, CalendarClock, CircleDollarSign, Landmark, MapPin, Scale, ShieldAlert, ShieldCheck, SlidersHorizontal, Sparkles, TrendingUp, Gauge } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { AssistantPanel } from "../components/AssistantPanel";
import { PageHeader } from "../components/PageHeader";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { RiskBadge } from "../components/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/StatePanel";
import { useAsync } from "../hooks/useAsync";
import type { Driver, ScenarioRecommendations, WhatIfConfig, WhatIfResult } from "../types";
import { crore, month, percent, text } from "../utils/format";
import { alertTypeLabel, displayValue, peerFieldLabel, peerFieldValue } from "../utils/presentation";

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  // React Router has already decoded path parameters. Trimming protects lookups
  // from accidental whitespace without changing the canonical identifier itself.
  const canonicalProjectId = projectId.trim();
  const detailState = useAsync(() => api.getProject(canonicalProjectId), [canonicalProjectId]);
  const trajectoryState = useAsync(() => api.getTrajectory(canonicalProjectId), [canonicalProjectId]);
  const explanationState = useAsync(() => api.getExplanation(canonicalProjectId), [canonicalProjectId]);
  const peersState = useAsync(() => api.getPeers(canonicalProjectId), [canonicalProjectId]);
  const alertsState = useAsync(() => api.getProjectAlerts(canonicalProjectId), [canonicalProjectId]);
  const priorityState = useAsync(() => api.getProjectPriority(canonicalProjectId), [canonicalProjectId]);
  const whatIfState = useAsync(() => api.getWhatIfConfig(canonicalProjectId), [canonicalProjectId]);
  const scenariosState = useAsync(() => api.getScenarios(canonicalProjectId), [canonicalProjectId]);

  if (detailState.loading) return <LoadingState label="Preparing project intelligence…" />;
  if (detailState.error) return <ErrorState message="Unable to load project details." onRetry={detailState.retry} />;
  if (!detailState.data) return <EmptyState title="Project not found" />;
  const detail = detailState.data;
  const latest = detail.latest_snapshot;
  const history = detail.historical_snapshots.map((snapshot) => ({
    month: snapshot.snapshot_month,
    progress: snapshot.physical_progress_pct,
    expenditure: snapshot.cumulative_expenditure_cr,
  }));
  const trajectoryData = (trajectoryState.data || []).map((point) => ({ ...point, probabilityPct: point.predicted_delay_probability_3m * 100 }));
  const explanation = explanationState.data || detail.explanation;

  return (
    <div className="page-stack command-center-page">
      <Link className="back-link" to="/projects">
        <ArrowLeft size={16} /> Back to Project Explorer
      </Link>
      
      <PageHeader 
        eyebrow={`${displayValue(detail.project_metadata.reporting_regime, "regime")} · ${month(latest.snapshot_month)}`} 
        title={displayValue(detail.project_metadata.project_name || canonicalProjectId)} 
        description={`${displayValue(detail.project_metadata.sector, "sector")} · ${displayValue(detail.project_metadata.state, "state")} · ${canonicalProjectId}`} 
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
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.15)]">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span>PROJECT TELEMETRY ACTIVE</span>
            </span>
          </>
        }
      />

      <section className="detail-hero">
        <article className="risk-card">
          <span className="eyebrow">Schedule Risk</span>
          <div className="risk-horizon">
            <div>
              <span>3-Month Delay Risk</span>
              <strong>{percent(detail.current_delay_probability_3m, 0)}</strong>
              <RiskBadge level={detail.risk_level} />
            </div>
            <div title="Estimated probability that the reported completion target moves later within the next six months.">
              <span>6-Month Delay Risk</span>
              <strong>{percent(detail.current_delay_probability_6m, 0)}</strong>
              {detail.delay_6m_model_status === "YELLOW" && <em>Longer-Horizon Signal</em>}
            </div>
          </div>
          <p>Schedule-risk horizons are estimated separately and are not combined.</p>
        </article>

        <article className="reliability-card">
          <span className="eyebrow">Data Reliability</span>
          <ReliabilityBadge score={detail.data_quality_score} />
          <strong>{detail.data_quality_score.toFixed(0)} / 100</strong>
          <p>Source-quality indicator. It is separate from model risk and does not measure certainty.</p>
        </article>

        <article className="detail-status-card">
          <span className="eyebrow">Current status</span>
          <div>
            <CalendarClock size={18} />
            <div>
              <strong className="block">{month(latest.current_target_doc?.slice(0, 7))}</strong>
              <span>Current target</span>
            </div>
          </div>
          <div>
            <TrendingUp size={18} />
            <div>
              <strong className="block">{latest.physical_progress_pct?.toFixed(1) ?? "-"}%</strong>
              <span>Physical progress</span>
            </div>
          </div>
        </article>
      </section>

      <section className="info-grid">
        <InfoCard icon={Landmark} title="Governance" rows={[["Ministry / Department", displayValue(detail.project_metadata.ministry_department, "ministry")], ["Agency", displayValue(detail.project_metadata.agency, "agency")], ["Identity Source", displayValue(detail.project_metadata.identity_source, "identity")]]} />
        <InfoCard icon={MapPin} title="Classification & Schedule" rows={[["Sector", displayValue(detail.project_metadata.sector, "sector")], ["State", displayValue(detail.project_metadata.state, "state")], ["Original Completion Date", month(latest.original_doc?.slice(0, 7))], ["Current Completion Target", month(latest.current_target_doc?.slice(0, 7))], ["Latest Snapshot", month(latest.snapshot_month)]]} />
        <InfoCard icon={CircleDollarSign} title="Financial position" rows={[["Original cost", crore(latest.original_cost_cr)], ["Revised / current cost", crore(latest.current_forecast_cost_cr)], ["Cumulative expenditure", crore(latest.cumulative_expenditure_cr)]]} />
        <InfoCard icon={ShieldCheck} title="Data Reliability" rows={[["Data Reliability", `${detail.data_quality_score.toFixed(1)} / 100`], ["Data-Quality Flags", latest.quality_flags || "No flags reported"], ["Identity Confidence", text(detail.project_metadata.identity_confidence)]]} />
      </section>

      <AssistantPanel projectId={canonicalProjectId} />

      {priorityState.loading ? <LoadingState label="Calculating deterministic intervention priority…" /> : priorityState.error ? <ErrorState message="Intervention priority could not be loaded." onRetry={priorityState.retry} /> : priorityState.data ? <ProjectPriorityPanel priority={priorityState.data} /> : null}

      <section className="panel chart-panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md mb-4">
        <div className="panel-heading pb-3 mb-2 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div>
            <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Model monitoring</span>
            <h2 className="text-sm font-bold text-[var(--text-primary)] mt-0.5">3-Month Delay-Risk Trajectory</h2>
          </div>
          <span className="quiet-note text-xs font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-3 py-1 rounded border border-[var(--border-subtle)]">
            Delay risk and data reliability are separate measures
          </span>
        </div>
        {trajectoryState.loading ? <LoadingState label="Loading risk trajectory…" /> : trajectoryState.error ? <ErrorState message="Risk trajectory could not be loaded." onRetry={trajectoryState.retry} /> : !trajectoryData.length ? <EmptyState title="No trajectory data available" /> :
          <ResponsiveContainer width="100%" height={330}>
            <LineChart data={trajectoryData} margin={{ top: 15, right: 18, left: 0, bottom: 5 }}>
              <CartesianGrid stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="snapshot_month" tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border-subtle)" }} tickLine={false} />
              <YAxis yAxisId="risk" domain={[0, 100]} unit="%" tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border-subtle)" }} tickLine={false} />
              <YAxis yAxisId="quality" orientation="right" domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border-subtle)" }} tickLine={false} />
              <Tooltip 
                formatter={(value, name) => name === "Delay risk" ? `${Number(value).toFixed(1)}%` : `${Number(value).toFixed(0)}/100`} 
                contentStyle={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border-subtle)", borderRadius: "8px", fontFamily: "monospace", fontSize: "11px" }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} />
              <Line yAxisId="risk" type="monotone" dataKey="probabilityPct" name="Delay risk" stroke="#f43f5e" strokeWidth={2.5} dot={{ r: 3, fill: "#f43f5e" }} />
              <Line yAxisId="quality" type="monotone" dataKey="data_quality_score" name="Data reliability" stroke="#0ea5e9" strokeWidth={2} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        }
      </section>

      <section className="dashboard-grid grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <HistoryChart title="Physical progress history" data={history} dataKey="progress" color="#0ea5e9" unit="%" />
        <HistoryChart title="Expenditure history" data={history} dataKey="expenditure" color="#10b981" unit=" Cr" />
      </section>

      <section className="explanation-grid">
        <DriverPanel title="Factors increasing risk" tone="risk" drivers={explanation.top_risk_drivers} />
        <DriverPanel title="Factors reducing risk" tone="protective" drivers={explanation.top_protective_drivers} />
      </section>
      
      <div className="explanation-note">
        <strong>Plain-language explanation</strong>
        <p>{explanation.explanation}</p>
      </div>

      {peersState.loading ? <LoadingState label="Loading peer comparison…" /> : peersState.error ? <ErrorState message="Peer comparison could not be loaded." onRetry={peersState.retry} /> : peersState.data ? <PeerPanel peers={peersState.data} /> : null}
      
      {alertsState.loading ? <LoadingState label="Loading project warnings…" /> : alertsState.error ? <ErrorState message="Project warnings could not be loaded." onRetry={alertsState.retry} /> : <AlertsPanel alerts={alertsState.data || []} />}
      
      {whatIfState.loading ? <LoadingState label="Loading scenario tools…" /> : whatIfState.error ? <ErrorState message="Scenario tools could not be loaded." onRetry={whatIfState.retry} /> : whatIfState.data ? <WhatIfPanel projectId={canonicalProjectId} config={whatIfState.data} scenarios={scenariosState.data} scenariosLoading={scenariosState.loading} scenariosError={Boolean(scenariosState.error)} retryScenarios={scenariosState.retry} /> : null}
      
      <div className="disclaimer">
        <ShieldCheck size={18} />
        <span>Risk estimates are predictive decision-support signals and do not establish causality.</span>
      </div>
    </div>
  );
}

function PeerPanel({ peers }: { peers: Awaited<ReturnType<typeof api.getPeers>> }) {
  return (
    <section className="panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] mb-4 overflow-hidden">
      <div className="panel-heading p-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)]">
        <div>
          <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Comparative context</span>
          <h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] mt-0.5">
            <Scale size={19} className="text-cyan-400" />
            <span>Peer Comparison</span>
          </h2>
        </div>
        <span className="quiet-note text-xs font-mono text-[var(--text-muted)] bg-[var(--bg-card)] px-3 py-1 rounded border border-[var(--border-subtle)]">
          {peers.peer_count} comparable projects
        </span>
      </div>
      {!peers.available ? (
        <EmptyState title={`Fewer than ${peers.minimum_peer_size} suitable peers`} />
      ) : (
        <div className="comparison-grid">
          <Comparison label="Physical Progress" project={peers.project_physical_progress_pct} peer={peers.peer_median_physical_progress_pct} unit="%" />
          <Comparison label="Expenditure Ratio" project={peers.project_expenditure_ratio_pct} peer={peers.peer_median_expenditure_ratio_pct} unit="%" />
          <Comparison label="3-Month Delay Risk" project={peers.project_delay_risk == null ? null : peers.project_delay_risk * 100} peer={peers.peer_median_delay_risk == null ? null : peers.peer_median_delay_risk * 100} unit="%" />
          <article className="comparison-card">
            <span>Risk Percentile</span>
            <strong>{peers.risk_percentile?.toFixed(0) ?? "—"}<small className="text-xs font-normal text-[var(--text-muted)] ml-1">th percentile</small></strong>
            <p>Progress percentile: {peers.progress_percentile?.toFixed(0) ?? "—"}</p>
          </article>
        </div>
      )}
      <p className="quiet-note p-4 pt-0 text-xs text-[var(--text-muted)]">
        Peer group: {Object.entries(peers.peer_group_definition).map(([key, value]) => `${peerFieldLabel(key)}: ${peerFieldValue(key, value)}`).join(" · ") || "broad portfolio cohort"}. Comparisons are descriptive, not causal.
      </p>
    </section>
  );
}

function Comparison({ label, project, peer, unit }: { label: string; project: number | null; peer: number | null; unit: string }) {
  const difference = project == null || peer == null ? null : project - peer;
  return (
    <article className="comparison-card">
      <span>{label}</span>
      <strong>{project?.toFixed(1) ?? "—"}{unit}</strong>
      <p>Peer median: {peer?.toFixed(1) ?? "—"}{unit}</p>
      <small>{difference == null ? "Difference unavailable" : `${difference >= 0 ? "+" : ""}${difference.toFixed(1)} percentage points`}</small>
    </article>
  );
}

function AlertsPanel({ alerts }: { alerts: Awaited<ReturnType<typeof api.getProjectAlerts>> }) {
  return (
    <section className="panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] mb-4 overflow-hidden">
      <div className="panel-heading p-4 border-b border-[var(--border-subtle)]">
        <div>
          <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Monitoring signals</span>
          <h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] mt-0.5">
            <ShieldAlert size={19} className="text-cyan-400" />
            <span>Active Warnings</span>
          </h2>
        </div>
      </div>
      {alerts.length ? (
        <div className="alert-card-grid">
          {alerts.map(alert => (
            <article key={alert.alert_id} className={`alert-card severity-${alert.severity.toLowerCase()}`}>
              <strong>{alertTypeLabel(alert.alert_type)}</strong>
              <span>{alert.severity}</span>
              <p>{alert.explanation}</p>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="No active deterministic warnings" />
      )}
    </section>
  );
}

function WhatIfPanel({ projectId, config, scenarios, scenariosLoading, scenariosError, retryScenarios }: { projectId: string; config: WhatIfConfig; scenarios: ScenarioRecommendations | null; scenariosLoading: boolean; scenariosError: boolean; retryScenarios: () => void }) {
  const initial = Object.fromEntries(config.controls.filter(item => item.current != null).map(item => [item.feature, item.current!])) as Record<string, number>;
  const [values, setValues] = useState(initial);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function run() { 
    setRunning(true); 
    setError(null); 
    try { 
      const changed = Object.fromEntries(config.controls.filter(item => values[item.feature] !== item.current).map(item => [item.feature, values[item.feature]])); 
      setResult(await api.runWhatIf(projectId, changed)); 
    } catch (cause) { 
      setError(cause instanceof Error ? cause.message : "Scenario failed"); 
    } finally { 
      setRunning(false); 
    } 
  }

  function reset() { 
    setValues(initial); 
    setResult(null); 
    setError(null); 
  }

  function load(feature: string, value: number) { 
    setValues({ ...initial, [feature]: value }); 
    setResult(null); 
    document.getElementById("what-if-simulator")?.scrollIntoView?.({ behavior: "smooth", block: "start" }); 
  }

  return (
    <>
      <section className="panel what-if-panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] mb-4 overflow-hidden" id="what-if-simulator">
        <div className="panel-heading p-4 border-b border-[var(--border-subtle)]">
          <div>
            <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Constrained simulation</span>
            <h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] mt-0.5">
              <SlidersHorizontal size={19} className="text-cyan-400" />
              <span>What-If Simulator</span>
            </h2>
          </div>
        </div>
        <div className="slider-grid">
          {config.controls.map(control => (
            <label key={control.feature}>
              <span>
                <strong>{control.label}</strong>
                <em>
                  <input 
                    aria-label={`${control.label} numeric value`} 
                    type="number" 
                    min={control.minimum} 
                    max={control.maximum} 
                    step={control.step} 
                    value={values[control.feature] ?? control.minimum} 
                    onChange={event => setValues({ ...values, [control.feature]: Number(event.target.value) })} 
                  />
                </em>
              </span>
              <input 
                type="range" 
                min={control.minimum} 
                max={control.maximum} 
                step={control.step} 
                value={values[control.feature] ?? control.minimum} 
                onChange={event => setValues({ ...values, [control.feature]: Number(event.target.value) })} 
              />
              <small>{control.minimum.toFixed(1)} to {control.maximum.toFixed(1)} · current {control.current?.toFixed(2) ?? "missing"}</small>
            </label>
          ))}
        </div>
        <div className="scenario-actions">
          <button className="primary-button" disabled={running} onClick={run}>
            {running ? "Evaluating…" : "Run scenario"}
          </button>
          <button className="secondary-button" disabled={running} onClick={reset}>
            Reset
          </button>
        </div>
        {error && <p className="inline-error p-4 text-xs text-rose-400">{error}</p>}
        {result && (
          <div className="scenario-result">
            <div>
              <span>Current risk</span>
              <strong>{percent(result.current_risk)}</strong>
              <small>{result.current_risk_level}</small>
            </div>
            <div>
              <span>Scenario risk</span>
              <strong>{percent(result.scenario_risk)}</strong>
              <small>{result.scenario_risk_level}</small>
            </div>
            <div>
              <span>Difference</span>
              <strong>{result.difference_percentage_points >= 0 ? "+" : ""}{result.difference_percentage_points.toFixed(2)} pp</strong>
            </div>
            <p>{result.scenario_explanation}</p>
          </div>
        )}
        <p className="quiet-note p-4 pt-0 text-xs text-[var(--text-muted)]">{config.disclaimer}</p>
      </section>
      
      <SuggestedScenarios 
        scenarios={scenarios} 
        loading={scenariosLoading} 
        failed={scenariosError} 
        onRetry={retryScenarios} 
        onLoad={load} 
      />
    </>
  );
}

const SCENARIO_DISCLAIMER = "Scenario estimates reflect model behavior under modified inputs and do not imply guaranteed causal impact.";

function SuggestedScenarios({ scenarios, loading, failed, onRetry, onLoad }: { scenarios: ScenarioRecommendations | null; loading: boolean; failed: boolean; onRetry: () => void; onLoad: (feature: string, value: number) => void }) {
  const recommendations = scenarios?.recommendations || [];
  return (
    <section className="panel scenario-panel rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] mb-4 overflow-hidden">
      <div className="panel-heading p-4 border-b border-[var(--border-subtle)]">
        <div>
          <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Model-based options</span>
          <h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] mt-0.5">
            <Sparkles size={19} className="text-cyan-400" />
            <span>Suggested Scenarios</span>
          </h2>
        </div>
      </div>
      {loading ? (
        <div className="scenario-compact-notice" aria-live="polite">
          <strong>Loading suggested scenarios…</strong>
        </div>
      ) : failed ? (
        <div className="scenario-compact-notice scenario-compact-error" role="alert">
          <strong>Scenario analysis is currently unavailable.</strong>
          <span>The rest of this project intelligence remains available.</span>
          <button className="secondary-button mt-2" onClick={onRetry}>Retry</button>
        </div>
      ) : recommendations.length > 0 ? (
        <div className="scenario-grid">
          {recommendations.map(item => (
            <article key={item.feature}>
              <span>Scenario {item.rank}</span>
              <strong>{item.label}</strong>
              <p>{item.wording}</p>
              <small>Feasibility score: {item.feasibility_score.toFixed(0)} / 100</small>
              <button className="secondary-button" onClick={() => onLoad(item.feature, item.scenario_value)}>
                Load into simulator
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="scenario-compact-notice">
          <strong>No suitable model-based scenario identified</strong>
          <span>No safe single-feature adjustment produced a lower model-estimated risk for this project.</span>
          <small>This does not mean the project cannot improve; it means the current model did not identify a safe single-variable scenario within the configured bounds.</small>
        </div>
      )}
      <p className="quiet-note p-4 pt-0 text-xs text-[var(--text-muted)]">{scenarios?.disclaimer || SCENARIO_DISCLAIMER}</p>
    </section>
  );
}

function InfoCard({ icon: Icon, title, rows }: { icon: typeof Landmark; title: string; rows: string[][] }) {
  return (
    <article className="panel info-card">
      <div className="info-title">
        <Icon size={16} />
        <h2>{title}</h2>
      </div>
      {rows.map(([label, value]) => (
        <div className="info-row" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </article>
  );
}

function HistoryChart({ title, data, dataKey, color, unit }: { title: string; data: Record<string, unknown>[]; dataKey: string; color: string; unit: string }) {
  return (
    <article className="panel chart-panel p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-md">
      <div className="panel-heading pb-3 mb-2 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">{title}</h2>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 5 }}>
          <CartesianGrid stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border-subtle)" }} tickLine={false} />
          <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border-subtle)" }} tickLine={false} />
          <Tooltip 
            formatter={(value) => `${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 1 })}${unit}`} 
            contentStyle={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border-subtle)", borderRadius: "8px", fontFamily: "monospace", fontSize: "11px" }}
          />
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.4} connectNulls={false} dot={{ r: 3, fill: color }} />
        </LineChart>
      </ResponsiveContainer>
    </article>
  );
}

function DriverPanel({ title, tone, drivers }: { title: string; tone: "risk" | "protective"; drivers: Driver[] }) {
  return (
    <article className={`panel driver-panel driver-${tone}`}>
      <div className="panel-heading pb-3 mb-2 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">{title}</h2>
      </div>
      {drivers.length ? (
        <ol>
          {drivers.map((driver) => (
            <li key={driver.feature}>
              <div>
                <strong>{driver.label}</strong>
                <span>{driver.feature}</span>
              </div>
              <em>{driver.observed_value == null ? "Missing" : String(driver.observed_value)}</em>
            </li>
          ))}
        </ol>
      ) : (
        <EmptyState title="No dominant factors returned" />
      )}
    </article>
  );
}

function ProjectPriorityPanel({ priority }: { priority: Awaited<ReturnType<typeof api.getProjectPriority>> }) {
  const label = (value: string) => value.replaceAll("_", " ").toLocaleLowerCase("en-IN").replace(/\b\w/g, letter => letter.toLocaleUpperCase("en-IN"));
  const arrow = priority.trajectory_status === "IMPROVING" ? "↓" : priority.trajectory_status === "STABLE" || priority.trajectory_status === "INSUFFICIENT_HISTORY" ? "→" : "↑";
  const points = (value: number | null) => value == null ? "Not available" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)} pp`;
  
  return (
    <section className="panel project-priority-panel">
      <div className="panel-heading p-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)]">
        <div>
          <span className="eyebrow block text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">Deterministic intervention intelligence</span>
          <h2 className="text-sm font-bold text-[var(--text-primary)] mt-0.5">Risk Trend & Intervention Priority</h2>
        </div>
        <span className={`priority-level priority-${priority.intervention_priority_level.toLowerCase()} inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider`}>
          {label(priority.intervention_priority_level)}
        </span>
      </div>
      <div className="project-priority-grid mt-3">
        <article>
          <span>Risk Trend</span>
          <strong className={`trajectory-label trajectory-${priority.trajectory_status.toLowerCase().replaceAll("_", "-")}`}>
            {arrow} {label(priority.trajectory_status)}
          </strong>
          <small>{priority.trajectory_status === "INSUFFICIENT_HISTORY" ? "Acceleration is not calculated without sufficient history." : "Based on consecutive frozen 3-month risk observations."}</small>
        </article>
        <article>
          <span>Last-Period Change</span>
          <strong>{points(priority.risk_change_1m)}</strong>
          <small>Probability-point movement displayed as percentage points.</small>
        </article>
        <article>
          <span>Recent 3-Period Change</span>
          <strong>{points(priority.risk_change_3m)}</strong>
          <small>{priority.risk_change_3m == null ? "Requires at least four observations." : "Latest versus approximately three reporting periods earlier."}</small>
        </article>
        <article>
          <span>Intervention Priority Score</span>
          <strong>{priority.intervention_priority_score.toFixed(1)} / 100</strong>
          <small>Review ranking, not a probability.</small>
        </article>
        <article>
          <span>Recommended Action</span>
          <strong>{label(priority.recommended_review_action)}</strong>
          <small>{priority.key_reason}</small>
        </article>
      </div>
    </section>
  );
}

