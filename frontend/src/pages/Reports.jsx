import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card.jsx';

export default function Reports() {
  const { id } = useParams();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">Reports</h1>
        <p className="mt-1 text-sm text-textMuted">
          Generated deliverables for project <span className="font-mono">{id}</span>.
        </p>
      </div>

      <Card title="Report Library">
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
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <p className="text-sm text-textMuted">PDF / Markdown export + report history — coming soon</p>
        </div>
      </Card>
    </div>
  );
}
