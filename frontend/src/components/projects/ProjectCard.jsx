import { useNavigate } from 'react-router-dom';

/**
 * Formats a budget number as USD currency, or returns a fallback string.
 */
function formatBudget(value) {
  if (value == null) return 'No budget set';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

/** Truncate a string to maxLen, appending '…' if cut. */
function truncate(str, maxLen) {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen).trimEnd() + '…';
}

/**
 * ProjectCard — a clickable card showing key project fields.
 * Clicking navigates to /projects/:id.
 *
 * @param {object} project — ProjectRead shape
 */
export default function ProjectCard({ project }) {
  const navigate = useNavigate();

  const handleClick = () => navigate(`/projects/${project.id}`);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      navigate(`/projects/${project.id}`);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="group flex flex-col gap-3 p-5 rounded-xl bg-surface border border-[var(--border)] cursor-pointer transition-colors duration-150 hover:border-accent/40 hover:bg-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      aria-label={`Open project: ${project.name}`}
    >
      {/* Name + company */}
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold text-text group-hover:text-accent transition-colors duration-150 leading-snug">
          {project.name}
        </h3>
        {project.company && (
          <p className="text-xs text-textMuted">{project.company}</p>
        )}
      </div>

      {/* Description snippet */}
      {project.description ? (
        <p className="text-xs text-textMuted leading-relaxed flex-1">
          {truncate(project.description, 120)}
        </p>
      ) : (
        <p className="text-xs text-textMuted/40 italic flex-1">No description</p>
      )}

      {/* Budget */}
      <div className="flex items-center justify-between pt-1 border-t border-[var(--border)]">
        <span className="text-xs text-textMuted">Budget</span>
        <span
          className={[
            'text-xs font-medium font-mono',
            project.budget_ceiling != null ? 'text-accent' : 'text-textMuted/60',
          ].join(' ')}
        >
          {formatBudget(project.budget_ceiling)}
        </span>
      </div>
    </div>
  );
}
