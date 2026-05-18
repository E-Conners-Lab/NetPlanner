import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card.jsx';

export default function TCO() {
  const { id } = useParams();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">TCO Calculator</h1>
        <p className="mt-1 text-sm text-textMuted">
          Total cost of ownership modelling for project <span className="font-mono">{id}</span>.
        </p>
      </div>

      <Card title="Cost Model">
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-textMuted/40"
            aria-hidden="true"
          >
            <rect x="4" y="2" width="16" height="20" rx="2" />
            <line x1="8" y1="6" x2="16" y2="6" />
            <line x1="8" y1="12" x2="16" y2="12" />
            <line x1="8" y1="18" x2="16" y2="18" />
            <line x1="12" y1="12" x2="12" y2="18" />
          </svg>
          <p className="text-sm text-textMuted">CapEx / OpEx breakdown + Recharts visualisations — coming soon</p>
        </div>
      </Card>
    </div>
  );
}
