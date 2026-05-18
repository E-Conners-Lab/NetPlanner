import { useLocation, useParams } from 'react-router-dom';

/**
 * Maps route patterns to human-readable section titles.
 * Checked in order — first match wins.
 */
const ROUTE_TITLES = [
  { pattern: /\/projects\/[^/]+\/advisor$/, label: 'AI Advisor' },
  { pattern: /\/projects\/[^/]+\/tco$/, label: 'TCO Calculator' },
  { pattern: /\/projects\/[^/]+\/comparison$/, label: 'Vendor Comparison' },
  { pattern: /\/projects\/[^/]+\/reports$/, label: 'Reports' },
  { pattern: /\/projects\/[^/]+$/, label: 'Project Overview' },
  { pattern: /^\/$/, label: 'Dashboard' },
];

function resolveTitle(pathname) {
  for (const { pattern, label } of ROUTE_TITLES) {
    if (pattern.test(pathname)) return label;
  }
  return 'NetPlanner';
}

/**
 * TopBar — renders the current section title and a right-side action slot.
 * The action slot is intentionally empty at Phase-0; Phase-1 will inject
 * context-aware actions (e.g. "New Project", "Export Report").
 */
export default function TopBar() {
  const location = useLocation();
  const { id: projectId } = useParams();
  const sectionTitle = resolveTitle(location.pathname);

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-[var(--border)] shrink-0 h-14">
      {/* Left: breadcrumb area */}
      <div className="flex items-center gap-2 min-w-0">
        {projectId && (
          <>
            <span className="text-sm text-textMuted truncate max-w-[120px]">
              Project
            </span>
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
          </>
        )}
        <h1 className="text-sm font-semibold text-text truncate">{sectionTitle}</h1>
      </div>

      {/* Right: action slot (placeholder for Phase-1 contextual actions) */}
      <div className="flex items-center gap-2" aria-label="Top bar actions">
        {/* Phase-1: inject <Button> components here */}
        <div className="w-1" aria-hidden="true" />
      </div>
    </header>
  );
}
