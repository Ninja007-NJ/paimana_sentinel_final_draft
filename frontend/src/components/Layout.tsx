import { 
  Menu, 
  X, 
  LayoutDashboard,
  Building2,
  TrendingUp,
  Bell,
  Bot,
  Gauge
} from "lucide-react";
import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { triggerButtonFeedback } from "../utils/haptics";
import { AssistantPanel } from "./AssistantPanel";

export function Layout() {
  const [open, setOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    localStorage.setItem("paimana_theme", "light");
  }, []);

  const handleToggleSentinel = (e: React.MouseEvent<HTMLElement>) => {
    triggerButtonFeedback(e, "pop");
    if (location.pathname === "/") {
      window.dispatchEvent(new CustomEvent("toggle-sentinel-ai"));
      return;
    }
    setAssistantOpen(current => !current);
  };

  return (
    <div className="app-shell">
      {/* 1. Clean Ordinary Left Fixed Sidebar */}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`} aria-label="Main navigation">
        <div className="sidebar-top-section">
          {/* Brand */}
          <div className="sidebar-brand">
            <div className="brand-logo">▲</div>
            <div className="brand-text-block">
              <strong className="brand-title">PAIMANA Sentinel</strong>
              <span className="brand-sub">MoSPI Decision Support</span>
            </div>
            <button 
              type="button"
              className="mobile-close" 
              onClick={() => setOpen(false)}
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          </div>

          {/* Primary Navigation: Dashboard, Projects, Intervention Policy, Analytics, Alerts */}
          <nav className="nav-list" aria-label="Primary navigation">
            <NavLink 
              to="/" 
              end 
              onClick={() => setOpen(false)} 
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <LayoutDashboard size={16} /> 
              <span>Dashboard</span>
            </NavLink>
            <NavLink 
              to="/projects" 
              onClick={() => setOpen(false)} 
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Building2 size={16} /> 
              <span>Projects</span>
            </NavLink>
            <NavLink 
              to="/priorities" 
              onClick={() => setOpen(false)} 
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Gauge size={16} /> 
              <span>Intervention Policy</span>
            </NavLink>
            <NavLink 
              to="/analytics" 
              onClick={() => setOpen(false)} 
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <TrendingUp size={16} /> 
              <span>Analytics</span>
            </NavLink>
            <NavLink 
              to="/alerts" 
              onClick={() => setOpen(false)} 
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Bell size={16} /> 
              <span>Alerts</span>
            </NavLink>
          </nav>
        </div>


        {/* Bottom Section: SIH Brief completely removed */}
        <div className="sidebar-footer">
          <div className="watermark-box">
            <div className="tricolor-bar">
              <div className="saffron" />
              <div className="white" />
              <div className="green" />
            </div>
            <div className="mospi-caption">
              Ministry of Statistics &amp; Programme Implementation<br />
              <strong className="text-gov">Government of India</strong>
            </div>
          </div>
        </div>
      </aside>

      {open && (
        <button 
          className="scrim" 
          onClick={() => setOpen(false)} 
          aria-label="Close navigation overlay" 
        />
      )}

      {/* 2. Main Column */}
      <div className="main-column">
        {/* Fixed Topbar */}
        <header className="topbar">
          <div className="topbar-left">
            <button 
              className="menu-button" 
              onClick={() => setOpen(prev => !prev)} 
              aria-label="Toggle navigation"
            >
              <Menu size={18} />
            </button>
            <div className="topbar-search">
              <input type="text" placeholder="Search projects, ministries, states..." aria-label="Search" />
              <span className="kbd-icon">⌘K</span>
            </div>
          </div>

          <div className="topbar-right">
            <NavLink 
              to="/priorities" 
              className="topbar-policy-chip hidden lg:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold text-amber-700 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 transition-all"
              title="Intervention Policy"
            >
              <Gauge size={13} className="text-amber-500" />
              <span>Intervention Policy</span>
            </NavLink>

            {/* Sentinel AI Copilot Collapsible trigger on right side of top navbar */}
            <button 
              type="button" 
              className="sentinel-ai-nav-btn"
              onClick={handleToggleSentinel}
              title="Toggle Sentinel AI Copilot"
              aria-label="Toggle Sentinel AI Copilot"
              aria-expanded={location.pathname === "/" ? undefined : assistantOpen}
            >
              <Bot size={15} className="text-cyan-400" />
              <span className="sentinel-btn-text">Sentinel AI</span>
              <span className="sentinel-ai-dot" />
            </button>

            <NavLink to="/alerts" className="notif-btn" title="Recent Alerts" aria-label="Recent Alerts">
              <Bell size={16} />
              <span className="notif-badge">3</span>
            </NavLink>

          </div>
        </header>

        {location.pathname !== "/" && assistantOpen && (
          <>
            <button
              type="button"
              className="global-assistant-scrim"
              aria-label="Close Sentinel AI"
              onClick={() => setAssistantOpen(false)}
            />
            <aside className="global-assistant-drawer" aria-label="Sentinel AI Assistant">
              <div className="global-assistant-header">
                <div>
                  <span className="eyebrow">Grounded portfolio assistant</span>
                  <strong>Sentinel AI</strong>
                </div>
                <button type="button" className="sentinel-close-btn" onClick={() => setAssistantOpen(false)} aria-label="Close Sentinel AI">
                  <X size={18} />
                </button>
              </div>
              <AssistantPanel />
            </aside>
          </>
        )}

        {/* The ONLY Scrollable Area */}
        <main className="main-scrollable-area">
          <div className="main-wrap">
            <Outlet />
          </div>
        </main>

        {/* Fixed Bottom Navbar / Footer */}
        <footer className="app-footer">
          <div>Ministry of Statistics and Programme Implementation, Government of India</div>
          <div>PAIMANA Sentinel v1.0 • For a Viksit Bharat</div>
          <div className="telemetry-tag">
            <span className="live-dot-pulse" /> Live Telemetry Active
          </div>
        </footer>
      </div>
    </div>
  );
}
