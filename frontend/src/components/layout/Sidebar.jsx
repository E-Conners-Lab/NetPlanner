import { NavLink, useLocation } from 'react-router-dom';

/* ── Icon helpers (inline SVG, no icon library dependency) ───── */
function IconGrid() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}
function IconBot() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      <circle cx="9" cy="16" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="16" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
function IconCalculator() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <line x1="8" y1="12" x2="16" y2="12" />
      <line x1="8" y1="18" x2="16" y2="18" />
      <line x1="12" y1="12" x2="12" y2="18" />
    </svg>
  );
}
function IconBarChart() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
      <line x1="2" y1="20" x2="22" y2="20" />
    </svg>
  );
}
function IconFileText() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

/* ── Shared nav-link style logic ────────────────────────────── */
const linkClass = ({ isActive }) =>
  [
    'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150',
    isActive
      ? 'bg-accent/10 text-accent'
      : 'text-textMuted hover:text-text hover:bg-surface',
  ].join(' ');

/* ── Sidebar section label ──────────────────────────────────── */
function SectionLabel({ children }) {
  return (
    <p className="px-3 mt-6 mb-1 text-xs font-semibold uppercase tracking-widest text-textMuted/60 select-none">
      {children}
    </p>
  );
}

/* ── Main component ─────────────────────────────────────────── */
export default function Sidebar() {
  // The Sidebar is rendered outside `<Routes>`, so `useParams()` returns
  // `{}` here — parse the project id from the path instead.
  const { pathname } = useLocation();
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const projectId = projectMatch?.[1] ?? null;

  return (
    <aside className="flex flex-col w-56 shrink-0 bg-surface border-r border-[var(--border)] h-full overflow-y-auto">
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-[var(--border)]">
        <span className="w-7 h-7 rounded-md bg-accent flex items-center justify-center shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0F1117" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
        </span>
        <span className="font-semibold text-text tracking-tight">NetPlanner</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3">
        {/* Global */}
        <SectionLabel>Workspace</SectionLabel>
        <NavLink to="/" end className={linkClass}>
          <IconGrid />
          Dashboard
        </NavLink>

        {/* Project-scoped links — only shown when a project is active */}
        {projectId && (
          <>
            <SectionLabel>Project</SectionLabel>

            <NavLink to={`/projects/${projectId}`} end className={linkClass}>
              <IconGrid />
              Overview
            </NavLink>

            <NavLink to={`/projects/${projectId}/advisor`} className={linkClass}>
              <IconBot />
              AI Advisor
            </NavLink>

            <NavLink to={`/projects/${projectId}/tco`} className={linkClass}>
              <IconCalculator />
              TCO Calculator
            </NavLink>

            <NavLink to={`/projects/${projectId}/comparison`} className={linkClass}>
              <IconBarChart />
              Comparison
            </NavLink>

            <NavLink to={`/projects/${projectId}/reports`} className={linkClass}>
              <IconFileText />
              Reports
            </NavLink>
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[var(--border)]">
        <p className="text-xs text-textMuted">NetPlanner</p>
      </div>
    </aside>
  );
}
