import Card from '../ui/Card.jsx';
import MatrixCell from './MatrixCell.jsx';

/**
 * ComparisonMatrix — renders the vendor × criteria grid and the summary paragraph.
 *
 * @param {object} comparison  — VendorComparisonRead
 */
export default function ComparisonMatrix({ comparison }) {
  const { vendors, criteria, matrix, summary } = comparison;

  return (
    <Card title="Comparison Matrix">
      {/* Scrollable wrapper so wide tables don't break the layout */}
      <div className="overflow-x-auto -mx-5">
        <table className="min-w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-[var(--border)]">
              {/* Top-left empty header cell */}
              <th className="pl-5 pr-4 py-3 text-left text-xs font-semibold text-textMuted uppercase tracking-wider w-40 shrink-0">
                Criterion
              </th>
              {vendors.map((vendor) => (
                <th
                  key={vendor}
                  className="px-4 py-3 text-left text-xs font-semibold text-text uppercase tracking-wider min-w-[200px]"
                >
                  {vendor}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {criteria.map((criterion, rowIndex) => (
              <tr
                key={criterion}
                className={[
                  'border-b border-[var(--border)]/60 last:border-0',
                  rowIndex % 2 === 0 ? '' : 'bg-bg/30',
                ].join(' ')}
              >
                {/* Criterion label */}
                <td className="pl-5 pr-4 py-4 text-xs font-medium text-textMuted align-top leading-relaxed">
                  {criterion}
                </td>

                {/* One cell per vendor */}
                {vendors.map((vendor) => {
                  const cell = matrix[vendor]?.[criterion] ?? {
                    value: '',
                    source: '',
                    confidence: 'unavailable',
                  };
                  return (
                    <td key={vendor} className="px-4 py-4 align-top">
                      <MatrixCell cell={cell} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      {summary && (
        <div className="mt-5 pt-4 border-t border-[var(--border)]">
          <p className="text-xs font-semibold text-textMuted uppercase tracking-wider mb-2">
            Summary
          </p>
          <p className="text-sm text-text leading-relaxed">{summary}</p>
        </div>
      )}
    </Card>
  );
}
