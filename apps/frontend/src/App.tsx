import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { Overview } from './pages/Overview';
import { LiveInference } from './pages/LiveInference';
import { DataIntegrity } from './pages/DataIntegrity';
import { ModelAssurance } from './pages/ModelAssurance';
import { AssuranceAnalytics } from './pages/AssuranceAnalytics';
import { DriftMonitor } from './pages/DriftMonitor';
import { IntegrityTestLab } from './pages/IntegrityTestLab';
import { PerformanceBenchmark } from './pages/PerformanceBenchmark';
import { EvidenceProvenance } from './pages/EvidenceProvenance';
import { VerificationConsole } from './pages/VerificationConsole';
import { EvidenceLedger } from './pages/EvidenceLedger';
import { Reports } from './pages/Reports';
import { GovernanceSystem } from './pages/GovernanceSystem';
import { EdgeHardwareRuntime } from './pages/EdgeHardwareRuntime';
import { Admin } from './pages/Admin';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Standalone Login Route */}
        <Route path="/login" element={<Login />} />

        {/* Console Layout Wrapped Routes */}
        <Route element={<Layout />}>
          <Route path="/overview" element={<Overview />} />
          <Route path="/live-inference" element={<LiveInference />} />
          <Route path="/data-integrity" element={<DataIntegrity />} />
          <Route path="/model-assurance" element={<ModelAssurance />} />
          <Route path="/assurance-analytics" element={<AssuranceAnalytics />} />
          <Route path="/drift-monitor" element={<DriftMonitor />} />
          <Route path="/integrity-test-lab" element={<IntegrityTestLab />} />
          <Route path="/performance-benchmark" element={<PerformanceBenchmark />} />
          <Route path="/evidence-and-provenance" element={<EvidenceProvenance />} />
          <Route path="/verification-console" element={<VerificationConsole />} />
          <Route path="/evidence-ledger" element={<EvidenceLedger />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/governance-system" element={<GovernanceSystem />} />
          <Route path="/edge-hardware-and-runtime" element={<EdgeHardwareRuntime />} />
          <Route path="/system-administration" element={<Admin />} />
          <Route path="/admin" element={<Admin />} />
        </Route>

        {/* Default Route */}
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
