import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { DetectionPhase } from './pages/DetectionPhase';
import { IncidentIntelligence } from './pages/IncidentIntelligence';
import { IncidentBriefing } from './pages/IncidentBriefing';
import { L1CommandInterface } from './pages/L1CommandInterface';
import { ApprovalWorkflow } from './pages/ApprovalWorkflow';
import { PlaybookExecution } from './pages/PlaybookExecution';
import { PostResolution } from './pages/PostResolution';
import { VetoWarning } from './pages/VetoWarning';
import { NetworkOverview } from './pages/NetworkOverview';
import { FinanceCore } from './pages/FinanceCore';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="detection" element={<DetectionPhase />} />
        <Route path="incidents" element={<IncidentIntelligence />} />
        <Route path="incidents/briefing" element={<IncidentBriefing />} />
        <Route path="incidents/l1-command" element={<L1CommandInterface />} />
        <Route path="incidents/approval" element={<ApprovalWorkflow />} />
        <Route path="incidents/playbook" element={<PlaybookExecution />} />
        <Route path="incidents/resolved" element={<PostResolution />} />
        <Route path="incidents/veto" element={<VetoWarning />} />
        <Route path="network" element={<NetworkOverview />} />
        <Route path="finance" element={<FinanceCore />} />
        <Route path="region/:regionId" element={<Dashboard />} />
        <Route path="system-health" element={<Dashboard />} />
        <Route path="settings" element={<Dashboard />} />
        <Route path="logs" element={<FinanceCore />} />
        <Route path="topology" element={<NetworkOverview />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
