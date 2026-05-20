import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { getProject } from '../../api/projects.js';

/** Section label per project sub-route. */
const SECTION_LABELS = {
  advisor: 'AI Advisor',
  tco: 'TCO Calculator',
  comparison: 'Vendor Comparison',
  reports: 'Reports',
};

function Chevron() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-textMuted shrink-0"
      aria-hidden="true"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

/**
 * One breadcrumb segment. Renders as a link when `to` is provided and the
 * segment is not the current page; otherwise renders as plain text.
 */
function Crumb({ to, current = false, children }) {
  if (current || !to) {
    return (
      <span
        className="text-sm font-semibold text-text truncate"
        aria-current={current ? 'page' : undefined}
      >
        {children}
      </span>
    );
  }
  return (
    <Link
      to={to}
      className="text-sm text-textMuted hover:text-text transition-colors truncate"
    >
      {children}
    </Link>
  );
}

/**
 * TopBar — renders a navigable breadcrumb chain
 * (Dashboard › [Project Name] › [Section]) and a right-side action slot.
 *
 * Each parent crumb is a real `<Link>`, so users can jump back to the
 * project overview or the dashboard from any sub-page without
 * round-tripping through the sidebar.
 */
export default function TopBar() {
  const location = useLocation();
  const { id: projectId } = useParams();

  // Identify the project sub-section (if any) from the URL path.
  const subMatch = location.pathname.match(/^\/projects\/[^/]+\/([^/]+)/);
  const sectionKey = subMatch?.[1];
  const sectionLabel = sectionKey ? SECTION_LABELS[sectionKey] : null;

  // Pull the project name to show in the middle crumb. One GET per project
  // change; failures fall back to the literal "Project" label.
  const [projectName, setProjectName] = useState(null);
  useEffect(() => {
    if (!projectId) {
      setProjectName(null);
      return undefined;
    }
    let cancelled = false;
    getProject(projectId)
      .then((res) => {
        if (!cancelled) setProjectName(res.data?.name ?? null);
      })
      .catch(() => {
        // Soft fail — keep the fallback label and don't surface to the user.
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const onDashboard = location.pathname === '/';
  const projectCrumbLabel = projectName || 'Project';

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-[var(--border)] shrink-0 h-14">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 min-w-0">
        <Crumb to={onDashboard ? null : '/'} current={onDashboard}>
          Dashboard
        </Crumb>

        {projectId && (
          <>
            <Chevron />
            <Crumb
              to={sectionLabel ? `/projects/${projectId}` : null}
              current={!sectionLabel}
            >
              {projectCrumbLabel}
            </Crumb>
          </>
        )}

        {sectionLabel && (
          <>
            <Chevron />
            <Crumb current>{sectionLabel}</Crumb>
          </>
        )}
      </nav>

      {/* Right: action slot for context-aware actions (e.g. "New Project"). */}
      <div className="flex items-center gap-2" aria-label="Top bar actions">
        <div className="w-1" aria-hidden="true" />
      </div>
    </header>
  );
}
