import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card.jsx';

export default function Advisor() {
  const { id } = useParams();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">AI Advisor</h1>
        <p className="mt-1 text-sm text-textMuted">
          Streaming LLM-powered guidance for project <span className="font-mono">{id}</span>.
        </p>
      </div>

      <Card title="Advisor Chat">
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
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <p className="text-sm text-textMuted">Streaming advisor chat interface — coming soon</p>
        </div>
      </Card>
    </div>
  );
}
