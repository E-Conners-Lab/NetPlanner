import Button from '../ui/Button.jsx';

/**
 * CriteriaFields — manages the dynamic list of 1+ evaluation criteria inputs.
 *
 * @param {string[]} criteria  — current list of criterion strings
 * @param {function} onChange  — (newCriteria: string[]) => void
 * @param {object}   errors    — { [index]: string } field-level error messages
 * @param {boolean}  disabled  — disables all inputs during generation
 */
export default function CriteriaFields({ criteria, onChange, errors = {}, disabled = false }) {
  const inputBase = [
    'w-full rounded-md px-3 py-2 text-sm bg-bg text-text',
    'border transition-colors duration-150',
    'placeholder:text-textMuted/50',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
    'focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' ');

  const handleChange = (index, value) => {
    const updated = criteria.map((c, i) => (i === index ? value : c));
    onChange(updated);
  };

  const handleAdd = () => {
    onChange([...criteria, '']);
  };

  const handleRemove = (index) => {
    if (criteria.length <= 1) return;
    onChange(criteria.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-textMuted">Evaluation Criteria (1+)</span>
        <Button
          variant="secondary"
          type="button"
          onClick={handleAdd}
          disabled={disabled}
          className="text-xs px-3 py-1 h-7"
        >
          + Add criterion
        </Button>
      </div>

      {criteria.map((criterion, index) => (
        <div key={index} className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <input
              id={`criterion-${index}`}
              type="text"
              value={criterion}
              onChange={(e) => handleChange(index, e.target.value)}
              disabled={disabled}
              placeholder={`Criterion ${index + 1}, e.g. Pricing`}
              className={[
                inputBase,
                errors[index]
                  ? 'border-red-500/60 focus-visible:ring-red-500'
                  : 'border-[var(--border)] hover:border-textMuted/40',
              ].join(' ')}
            />
            {criteria.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemove(index)}
                disabled={disabled}
                aria-label={`Remove criterion ${index + 1}`}
                className="shrink-0 p-1.5 rounded text-textMuted hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
          {errors[index] && (
            <p className="text-xs text-red-400">{errors[index]}</p>
          )}
        </div>
      ))}
    </div>
  );
}
