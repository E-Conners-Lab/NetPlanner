import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar.jsx';
import TopBar from './components/layout/TopBar.jsx';
import Dashboard from './pages/Dashboard.jsx';
import ProjectDetail from './pages/ProjectDetail.jsx';
import Advisor from './pages/Advisor.jsx';
import TCO from './pages/TCO.jsx';
import Comparison from './pages/Comparison.jsx';
import Reports from './pages/Reports.jsx';

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-bg text-text">
      {/* ── Left sidebar ────────────────────────────────────── */}
      <Sidebar />

      {/* ── Main content column ─────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />

        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/advisor" element={<Advisor />} />
            <Route path="/projects/:id/tco" element={<TCO />} />
            <Route path="/projects/:id/comparison" element={<Comparison />} />
            <Route path="/projects/:id/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
