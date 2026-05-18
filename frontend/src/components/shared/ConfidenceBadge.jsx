import Badge from '../ui/Badge.jsx';

/**
 * ConfidenceBadge — visual indicator of data confidence level.
 *
 * @param {'confirmed'|'estimated'|'unavailable'} confidence
 * @param {string} [className]
 */
const CONFIDENCE_CONFIG = {
  confirmed: {
    color: 'green',
    label: 'Confirmed',
  },
  estimated: {
    color: 'amber',
    label: 'Estimated',
  },
  unavailable: {
    color: 'muted',
    label: 'Unavailable',
  },
};

export default function ConfidenceBadge({ confidence, className = '' }) {
  const config = CONFIDENCE_CONFIG[confidence] ?? CONFIDENCE_CONFIG.unavailable;

  return (
    <Badge color={config.color} className={className}>
      {config.label}
    </Badge>
  );
}
