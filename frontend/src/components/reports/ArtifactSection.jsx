/**
 * ArtifactSection — a grouped list of checkable artifacts within the picker.
 *
 * Renders a section title, loading/error/empty states, and a checkbox row
 * for each item. Selection is managed externally via selectedIds + onToggle.
 *
 * @param {string}        title        — section heading
 * @param {object[]|null} items        — fetched items (null while loading)
 * @param {boolean}       loading      — show loading state
 * @param {string|null}   error        — show error state
 * @param {string}        emptyMessage — shown when items is an empty array
 * @param {function}      renderLabel  — (item) => React node — item label content
 * @param {Set<string>}   selectedIds  — set of currently selected ref IDs
 * @param {function}      onToggle     — (id: string) => void — called on checkbox change
 */
export default function ArtifactSection({
  title,
  items,
  loading,
  error,
  emptyMessage,
  renderLabel,
  selectedIds,
  onToggle,
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2">
        {title}
      </h3>

      {loading && (
        <p className="text-sm text-textMuted py-2 pl-1">Loading…</p>
      )}

      {!loading && error && (
        <p className="text-sm text-red-400 py-2 pl-1">{error}</p>
      )}

      {!loading && !error && items !== null && items.length === 0 && (
        <p className="text-sm text-textMuted/60 py-2 pl-1 italic">{emptyMessage}</p>
      )}

      {!loading && !error && items !== null && items.length > 0 && (
        <div className="space-y-1">
          {items.map((item) => {
            const checked = selectedIds.has(item.id);
            return (
              <label
                key={item.id}
                className={[
                  'flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer',
                  'border transition-colors duration-100',
                  checked
                    ? 'border-accent/40 bg-accent/8'
                    : 'border-transparent hover:border-[var(--border)] hover:bg-bg/40',
                ].join(' ')}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(item.id)}
                  className="mt-0.5 shrink-0 accent-[#F59E0B] w-4 h-4 rounded cursor-pointer"
                />
                <span className="min-w-0 flex-1">{renderLabel(item)}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
