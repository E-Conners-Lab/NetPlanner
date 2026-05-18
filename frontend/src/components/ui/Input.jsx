/**
 * Input — styled text input with optional label.
 *
 * @param {string}   [label]       — label text rendered above the input
 * @param {string}   [id]          — links label htmlFor; auto-derived from label if omitted
 * @param {string}   [placeholder]
 * @param {string}   [value]
 * @param {function} [onChange]
 * @param {boolean}  [disabled]
 * @param {string}   [type]        — input type attribute (default 'text')
 * @param {string}   [className]   — extra classes applied to the wrapper div
 * @param {string}   [error]       — error message displayed below the input
 */
export default function Input({
  label,
  id,
  placeholder,
  value,
  onChange,
  disabled = false,
  type = 'text',
  className = '',
  error,
  ...rest
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={['flex flex-col gap-1', className].join(' ')}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-xs font-medium text-textMuted"
        >
          {label}
        </label>
      )}

      <input
        id={inputId}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        className={[
          'w-full rounded-md px-3 py-2 text-sm bg-bg text-text',
          'border transition-colors duration-150',
          'placeholder:text-textMuted/50',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          error
            ? 'border-red-500/60 focus-visible:ring-red-500'
            : 'border-[var(--border)] hover:border-textMuted/40',
        ].join(' ')}
        {...rest}
      />

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
