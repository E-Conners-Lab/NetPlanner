import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card.jsx';

export default function Comparison() {
  const { id } = useParams();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">Vendor Comparison</h1>
        <p className="mt-1 text-sm text-textMuted">
          Side-by-side vendor analysis for project <span className="font-mono">{id}</span>.
        </p>
      </div>

      <Card title="Comparison Matrix">
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
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
            <line x1="2" y1="20" x2="22" y2="20" />
          </svg>
          <p className="text-sm text-textMuted">Vendor comparison table + radar charts — coming soon</p>
        </div>
      </Card>
    </div>
  );
}
