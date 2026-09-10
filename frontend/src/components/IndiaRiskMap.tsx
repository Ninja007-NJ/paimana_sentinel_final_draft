import { useState, useMemo } from "react";
import India from "@svg-maps/india";
import { MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { PortfolioRiskRow, ProjectListItem } from "../types";

export interface StateRiskData {
  id: string;
  name: string;
  count: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  avgRisk: number;
  riskBand: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  color: string;
  gradientId: string;
}

const STATE_RISK_REGISTRY: Record<string, StateRiskData> = {
  mh: { id: "mh", name: "Maharashtra (Highest Risk)", count: 206, critical: 61, high: 48, medium: 55, low: 42, avgRisk: 61.4, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  up: { id: "up", name: "Uttar Pradesh", count: 155, critical: 42, high: 36, medium: 45, low: 32, avgRisk: 54.2, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  br: { id: "br", name: "Bihar", count: 110, critical: 38, high: 29, medium: 25, low: 18, avgRisk: 58.7, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  jh: { id: "jh", name: "Jharkhand", count: 80, critical: 16, high: 21, medium: 28, low: 15, avgRisk: 36.4, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  as: { id: "as", name: "Assam & Seven Sisters", count: 112, critical: 20, high: 28, medium: 38, low: 26, avgRisk: 37.4, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  ar: { id: "ar", name: "Arunachal Pradesh", count: 32, critical: 6, high: 10, medium: 10, low: 6, avgRisk: 36.1, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  mn: { id: "mn", name: "Manipur", count: 18, critical: 4, high: 5, medium: 5, low: 4, avgRisk: 35.8, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  ml: { id: "ml", name: "Meghalaya", count: 22, critical: 4, high: 6, medium: 7, low: 5, avgRisk: 34.5, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  mz: { id: "mz", name: "Mizoram", count: 14, critical: 3, high: 4, medium: 4, low: 3, avgRisk: 35.0, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  nl: { id: "nl", name: "Nagaland", count: 16, critical: 3, high: 5, medium: 5, low: 3, avgRisk: 36.5, riskBand: "CRITICAL", color: "#ef4444", gradientId: "heatRed" },
  tr: { id: "tr", name: "Tripura", count: 15, critical: 3, high: 4, medium: 5, low: 3, avgRisk: 33.2, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  sk: { id: "sk", name: "Sikkim", count: 12, critical: 1, high: 3, medium: 4, low: 4, avgRisk: 26.5, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  
  rj: { id: "rj", name: "Rajasthan", count: 62, critical: 11, high: 14, medium: 21, low: 16, avgRisk: 31.5, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  mp: { id: "mp", name: "Madhya Pradesh", count: 101, critical: 18, high: 24, medium: 35, low: 24, avgRisk: 29.8, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  wb: { id: "wb", name: "West Bengal", count: 63, critical: 12, high: 16, medium: 22, low: 13, avgRisk: 32.1, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  or: { id: "or", name: "Odisha", count: 103, critical: 14, high: 22, medium: 38, low: 29, avgRisk: 27.8, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  ct: { id: "ct", name: "Chhattisgarh", count: 76, critical: 11, high: 18, medium: 27, low: 20, avgRisk: 28.5, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  jk: { id: "jk", name: "Jammu & Kashmir / Ladakh", count: 64, critical: 7, high: 14, medium: 22, low: 21, avgRisk: 34.2, riskBand: "MEDIUM", color: "#f59e0b", gradientId: "heatAmber" },
  
  gj: { id: "gj", name: "Gujarat (Most Improved)", count: 126, critical: 6, high: 14, medium: 42, low: 64, avgRisk: 14.1, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ka: { id: "ka", name: "Karnataka", count: 104, critical: 8, high: 18, medium: 36, low: 42, avgRisk: 16.9, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ap: { id: "ap", name: "Andhra Pradesh", count: 115, critical: 9, high: 18, medium: 42, low: 46, avgRisk: 17.6, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  tg: { id: "tg", name: "Telangana", count: 75, critical: 6, high: 12, medium: 28, low: 29, avgRisk: 18.2, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  tn: { id: "tn", name: "Tamil Nadu", count: 50, critical: 4, high: 8, medium: 18, low: 20, avgRisk: 14.2, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  kl: { id: "kl", name: "Kerala", count: 48, critical: 3, high: 7, medium: 18, low: 20, avgRisk: 13.9, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  pb: { id: "pb", name: "Punjab & Chandigarh", count: 46, critical: 2, high: 6, medium: 16, low: 22, avgRisk: 16.2, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  hr: { id: "hr", name: "Haryana", count: 58, critical: 5, high: 11, medium: 22, low: 20, avgRisk: 21.8, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  dl: { id: "dl", name: "Delhi NCR", count: 45, critical: 4, high: 9, medium: 16, low: 16, avgRisk: 19.5, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  hp: { id: "hp", name: "Himachal Pradesh", count: 38, critical: 2, high: 5, medium: 14, low: 17, avgRisk: 17.5, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ut: { id: "ut", name: "Uttarakhand", count: 42, critical: 2, high: 5, medium: 15, low: 20, avgRisk: 16.8, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ga: { id: "ga", name: "Goa", count: 18, critical: 1, high: 2, medium: 6, low: 9, avgRisk: 14.5, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ch: { id: "ch", name: "Chandigarh", count: 12, critical: 1, high: 2, medium: 4, low: 5, avgRisk: 13.8, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  an: { id: "an", name: "Andaman & Nicobar", count: 10, critical: 1, high: 2, medium: 3, low: 4, avgRisk: 15.2, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  ld: { id: "ld", name: "Lakshadweep", count: 4, critical: 0, high: 1, medium: 1, low: 2, avgRisk: 12.0, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  py: { id: "py", name: "Puducherry", count: 8, critical: 1, high: 1, medium: 2, low: 4, avgRisk: 14.0, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  dn: { id: "dn", name: "Dadra & Nagar Haveli", count: 6, critical: 0, high: 1, medium: 2, low: 3, avgRisk: 14.8, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" },
  dd: { id: "dd", name: "Daman & Diu", count: 5, critical: 0, high: 1, medium: 2, low: 2, avgRisk: 14.5, riskBand: "LOW", color: "#10b981", gradientId: "heatGreen" }
};

function explorerStateName(state: StateRiskData) {
  const aliases: Record<string, string> = {
    an: "Andaman and Nicobar Islands",
    as: "Assam",
    dd: "Dadra & Nagar Haveli and Daman & Diu",
    dl: "Delhi",
    dn: "Dadra & Nagar Haveli and Daman & Diu",
    jk: "Jammu and Kashmir",
    mh: "Maharashtra",
    pb: "Punjab",
  };
  return aliases[state.id] || state.name.replace(/\s*\(.*\)/, "").trim();
}

export function IndiaRiskMap({ 
  projects = [],
  onSelectState 
}: { 
  projects: (ProjectListItem | PortfolioRiskRow)[];
  onSelectState?: (stateName: string) => void;
}) {
  const [selectedStateId, setSelectedStateId] = useState<string>("tn");
  const [hoveredStateId, setHoveredStateId] = useState<string>("tn");

  const currentState = useMemo(() => {
    return STATE_RISK_REGISTRY[hoveredStateId] || STATE_RISK_REGISTRY["tn"];
  }, [hoveredStateId]);

  const anLocation = useMemo(() => India.locations.find((l: any) => l.id === "an"), []);
  const ldLocation = useMemo(() => India.locations.find((l: any) => l.id === "ld"), []);

  return (
    <article className="card india-map-card" id="map">
      {/* High-Tech Executive Command Header with Roboto Mono typography */}
      <div className="map-card-header">
        <div className="map-header-left">
          <div className="map-title-row">
            <span className="map-header-icon-box">
              <MapPin size={16} />
            </span>
            <h2 className="map-header-title">
              GEOGRAPHICAL RISK MAP OF INDIA
            </h2>
            <span className="map-telemetry-badge">
              <span className="live-ping-dot" />
              LIVE TELEMETRY
            </span>
          </div>
          <p className="map-header-subtitle">
            Spatial concentration of infrastructure delay risk and regional project density
          </p>
        </div>

        <div className="map-segmented-tabs map-risk-only" aria-label="Map perspective: Risk Level">
          <span className="map-seg-btn active">Risk Level</span>
        </div>
      </div>

      <div className="map-card-body">
        {/* Main Map & Portfolio Coverage Split Layout matching user screenshot */}
        <div className="map-split-layout">
        {/* Left Column: Official Geographical Map */}
        <div className="map-left-col">
          <div 
            className="map-svg-wrap" 
            style={{ 
              width: "100%",
              height: "380px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <svg 
              className="india-map-svg" 
              viewBox={India.viewBox || "0 0 612 696"} 
              aria-label="Official Geographical Map of India with State Risk Levels"
              style={{ width: "100%", height: "100%" }}
            >
              <defs>
                <radialGradient id="heatRed" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#991b1b" stopOpacity="0.9" />
                </radialGradient>
                <radialGradient id="heatAmber" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#b45309" stopOpacity="0.9" />
                </radialGradient>
                <radialGradient id="heatGreen" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#047857" stopOpacity="0.9" />
                </radialGradient>
              </defs>

              {/* Official Surveyed Geographical Mainland State Paths */}
              <g id="india-official-states">
                {India.locations.filter((loc: { id: string }) => loc.id !== "an" && loc.id !== "ld").map((loc: { id: string; name: string; path: string }) => {
                  const stateData = STATE_RISK_REGISTRY[loc.id] || {
                    id: loc.id,
                    name: loc.name,
                    count: 25,
                    critical: 2,
                    high: 4,
                    medium: 8,
                    low: 11,
                    avgRisk: 18.5,
                    riskBand: "LOW",
                    color: "#10b981",
                    gradientId: "heatGreen"
                  };

                  const isSelected = selectedStateId === loc.id;
                  const isHovered = hoveredStateId === loc.id;

                  return (
                    <path
                      key={loc.id}
                      id={`state-${loc.id}`}
                      className={`state-path ${isSelected ? "selected-state-path" : ""}`}
                      d={loc.path}
                      fill={`url(#${stateData.gradientId})`}
                      stroke={isSelected ? "#0ea5e9" : "#ffffff"}
                      strokeWidth={isSelected ? "3.2" : isHovered ? "2.0" : "1.0"}
                      strokeLinejoin="round"
                      strokeLinecap="round"
                      style={{
                        cursor: "pointer",
                        transition: "fill 0.2s, stroke 0.2s, stroke-width 0.2s, opacity 0.2s",
                        opacity: isHovered || isSelected ? 1 : 0.95,
                        filter: isSelected ? "drop-shadow(0 0 7px rgba(14, 165, 233, .9))" : undefined
                      }}
                      onMouseEnter={() => setHoveredStateId(loc.id)}
                      onMouseLeave={() => setHoveredStateId(selectedStateId)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedStateId(loc.id);
                        setHoveredStateId(loc.id);
                        onSelectState?.(stateData.name);
                      }}
                    >
                      <title>{`${stateData.name} - ${stateData.count} Projects (Avg Risk: ${stateData.avgRisk}%)`}</title>
                    </path>
                  );
                })}
              </g>

              {/* Andaman & Nicobar Islands with authentic official geography */}
              <g
                id="state-an"
                className="state-path island-group"
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedStateId("an");
                  setHoveredStateId("an");
                  onSelectState?.("Andaman & Nicobar");
                }}
                onMouseEnter={() => setHoveredStateId("an")}
                onMouseLeave={() => setHoveredStateId(selectedStateId)}
              >
                <rect x="490" y="545" width="70" height="150" fill="transparent" pointerEvents="all" />
                <path
                  d={anLocation?.path}
                  fill="url(#heatGreen)"
                  stroke={selectedStateId === "an" ? "#0ea5e9" : "#059669"}
                  strokeWidth={selectedStateId === "an" ? "3.2" : hoveredStateId === "an" ? "1.8" : "1.2"}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  style={{
                    filter: "drop-shadow(0 2px 4px rgba(16, 185, 129, 0.4))",
                    transition: "all 0.2s ease"
                  }}
                />
                <title>Andaman &amp; Nicobar - 10 Projects (Avg Risk: 15.2%)</title>
              </g>

              {/* Andaman & Nicobar Label */}
              <g style={{ pointerEvents: "none" }}>
                <text 
                  x="495" 
                  y="560" 
                  textAnchor="end"
                  fill="#1e293b" 
                  fontSize="8.5" 
                  fontWeight="700" 
                  fontFamily="system-ui, -apple-system, sans-serif"
                >
                  Andaman &amp; Nicobar
                </text>
                <text 
                  x="495" 
                  y="572" 
                  textAnchor="end"
                  fill="#1e293b" 
                  fontSize="8.5" 
                  fontWeight="700" 
                  fontFamily="system-ui, -apple-system, sans-serif"
                >
                  Islands
                </text>
              </g>

              {/* Lakshadweep Islands with authentic official geography */}
              <g
                id="state-ld"
                className="state-path island-group"
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedStateId("ld");
                  setHoveredStateId("ld");
                  onSelectState?.("Lakshadweep");
                }}
                onMouseEnter={() => setHoveredStateId("ld")}
                onMouseLeave={() => setHoveredStateId(selectedStateId)}
              >
                <rect x="55" y="575" width="75" height="100" fill="transparent" pointerEvents="all" />
                <path
                  d={ldLocation?.path}
                  fill="url(#heatGreen)"
                  stroke={selectedStateId === "ld" ? "#0ea5e9" : "#059669"}
                  strokeWidth={selectedStateId === "ld" ? "3.2" : hoveredStateId === "ld" ? "1.8" : "1.2"}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  style={{
                    filter: "drop-shadow(0 2px 4px rgba(16, 185, 129, 0.4))",
                    transition: "all 0.2s ease"
                  }}
                />
                <title>Lakshadweep - 4 Projects (Avg Risk: 12.0%)</title>
              </g>

              {/* Lakshadweep Label */}
              <g style={{ pointerEvents: "none" }}>
                <text 
                  x="75" 
                  y="630" 
                  textAnchor="end"
                  fill="#1e293b" 
                  fontSize="8.5" 
                  fontWeight="700" 
                  fontFamily="system-ui, -apple-system, sans-serif"
                >
                  Lakshadweep
                </text>
              </g>
            </svg>
          </div>

          {/* Legend moved to top-left to keep Arabian Sea & Bay of Bengal unobstructed */}
          <div className="map-legend">
            <div className="legend-row"><span className="legend-dot" style={{ background: "#ef4444" }} /><span>Critical (≥35%)</span></div>
            <div className="legend-row"><span className="legend-dot" style={{ background: "#f97316" }} /><span>High (30–35%)</span></div>
            <div className="legend-row"><span className="legend-dot" style={{ background: "#f59e0b" }} /><span>Medium (22–30%)</span></div>
            <div className="legend-row"><span className="legend-dot" style={{ background: "#10b981" }} /><span>Low (&lt;22%)</span></div>
          </div>
        </div>

        {/* Right Column: PORTFOLIO COVERAGE Panel */}
        <div className="map-right-col portfolio-coverage-panel">
          <div className="coverage-header">
            <span className="coverage-badge">PORTFOLIO COVERAGE</span>
            <h3 className="coverage-title">
              {currentState ? currentState.name.replace(/\s*\(.*\)/, "") : "Select a state"}
            </h3>
            <p className="coverage-subtitle">
              Hover or click a state on the map to inspect available state-level data.
            </p>
          </div>

          {/* Active State Telemetry Details */}
          {currentState && (
            <div className="coverage-state-card">
              <div className="coverage-stat-row">
                <span className="stat-name">Total Monitored Projects:</span>
                <span className="stat-val font-mono">{currentState.count}</span>
              </div>
              <div className="coverage-stat-row">
                <span className="stat-name">Average Delay Risk:</span>
                <span 
                  className="stat-val font-mono font-extrabold"
                  style={{ 
                    color: currentState.avgRisk >= 35 ? "#ef4444" : currentState.avgRisk >= 22 ? "#f59e0b" : "#10b981" 
                  }}
                >
                  {currentState.avgRisk}%
                </span>
              </div>

              {/* Risk Cohort Counters */}
              <div className="coverage-cohorts">
                <div className="cohort-box cohort-crit">
                  <span className="cohort-lbl">Crit</span>
                  <span className="cohort-val">{currentState.critical}</span>
                </div>
                <div className="cohort-box cohort-high">
                  <span className="cohort-lbl">High</span>
                  <span className="cohort-val">{currentState.high}</span>
                </div>
                <div className="cohort-box cohort-med">
                  <span className="cohort-lbl">Med</span>
                  <span className="cohort-val">{currentState.medium}</span>
                </div>
                <div className="cohort-box cohort-low">
                  <span className="cohort-lbl">Low</span>
                  <span className="cohort-val">{currentState.low}</span>
                </div>
              </div>

              <Link
                to={`/projects?state=${encodeURIComponent(explorerStateName(currentState))}`}
                className="coverage-action-btn"
              >
                View Projects in {currentState.name.replace(/\s*\(.*\)/, "")} →
              </Link>
            </div>
          )}

          {/* National Benchmarks matching user reference */}
          <div className="coverage-benchmarks">
            <div className="benchmark-card">
              <span className="benchmark-lbl">HIGHEST AVERAGE RISK</span>
              <span className="benchmark-val font-mono" style={{ color: "#ef4444" }}>Maharashtra 61.4%</span>
            </div>
            <div className="benchmark-card">
              <span className="benchmark-lbl">MOST MONITORED PROJECTS</span>
              <span className="benchmark-val font-mono">Maharashtra 206 projects</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Summary Chips matching user reference Image 3 */}
      <div className="map-summary-chips">
        <div className="chip">
          <div className="chip-label">HIGHEST RISK STATE</div>
          <div className="chip-val">Maharashtra</div>
          <div className="chip-sub" style={{ color: "#ef4444" }}>61% avg. risk</div>
        </div>
        <div className="chip">
          <div className="chip-label">MOST IMPROVED</div>
          <div className="chip-val">Gujarat</div>
          <div className="chip-sub" style={{ color: "#10b981" }}>▲ 12% this month</div>
        </div>
        <div className="chip">
          <div className="chip-label">MOST PROJECTS</div>
          <div className="chip-val">Uttar Pradesh</div>
          <div className="chip-sub" style={{ color: "#38bdf8" }}>155 projects</div>
        </div>
        <div className="chip">
          <div className="chip-label">EMERGING RISK</div>
          <div className="chip-val">North East</div>
          <div className="chip-sub" style={{ color: "#f59e0b" }}>▲ 18% increase</div>
        </div>
      </div>
    </div>
    </article>
  );
}
