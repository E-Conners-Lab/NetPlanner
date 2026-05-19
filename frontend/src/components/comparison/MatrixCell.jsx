import ConfidenceBadge from '../shared/ConfidenceBadge.jsx';

/**
 * MatrixCell — renders a single cell in the comparison matrix.
 *
 * @param {{ value: string, source: string, confidence: 'confirmed'|'estimated'|'unavailable' }} cell
 */
export default function MatrixCell({ cell }) {
  const isUnavailable = cell.confidence === 'unavailable';

  return (
    <div className="flex flex-col gap-1.5 min-w-0">
      <p
        className={[
          'font-mono text-xs leading-relaxed',
          isUnavailable ? 'text-textMuted/60 italic' : 'text-text',
        ].join(' ')}
      >
        {isUnavailable ? 'Not available' : cell.value}
      </p>

      <ConfidenceBadge confidence={cell.confidence} />

      {!isUnavailable && cell.source && (
        <a
          href={cell.source}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-accent hover:underline truncate max-w-[180px]"
          title={cell.source}
        >
          Source ↗
        </a>
      )}
    </div>
  );
}
