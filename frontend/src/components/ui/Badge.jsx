/**
 * Badge — small pill label.
 *
 * @param {'green'|'amber'|'red'|'blue'|'muted'} [color='muted']
 * @param {React.ReactNode} children
 * @param {string}          [className]
 */
export default function Badge({ color = 'muted', children, className = '' }) {
  const colorMap = {
    green: 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30',
    red:   'bg-red-500/15 text-red-400 ring-1 ring-red-500/30',
    blue:  'bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30',
    muted: 'bg-textMuted/10 text-textMuted ring-1 ring-textMuted/20',
  };

  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        colorMap[color] ?? colorMap.muted,
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}
