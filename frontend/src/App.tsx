import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider } from './components/ui/Toast';
import { AppShell } from './components/layout/AppShell';
import { Home } from './pages/Home';
import { NotFound } from './pages/NotFound';
import { DashboardPage } from './pages/Dashboard';
import { DocumentsPage } from './pages/Documents';
import { ReviewQueuePage } from './pages/ReviewQueue';
import { AiAssistantPage } from './pages/AiAssistant';
import { WorkflowBuilderPage } from './pages/WorkflowBuilder';
import { ApprovalsPage } from './pages/Approvals';
import { AnalyticsPage } from './pages/Analytics';
import { AuditLogPage } from './pages/AuditLog';
import { IntegrationsPage } from './pages/Integrations';
import { SettingsPage } from './pages/Settings';
import { DevDesignSystemPage } from './pages/DevDesignSystem';

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />

            {/* Every /app/* route renders through AppShell (single shared
                shell — see AppShell.tsx). Not access-controlled yet: real
                auth/session gating is added in the auth phase. */}
            <Route path="/app" element={<AppShell />}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="review-queue" element={<ReviewQueuePage />} />
              <Route path="assistant" element={<AiAssistantPage />} />
              <Route path="workflows" element={<WorkflowBuilderPage />} />
              <Route path="approvals" element={<ApprovalsPage />} />
              <Route path="analytics" element={<AnalyticsPage />} />
              <Route path="audit-log" element={<AuditLogPage />} />
              <Route path="integrations" element={<IntegrationsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Never present in a production build — see the DEV guard. */}
            {import.meta.env.DEV && <Route path="/dev/design-system" element={<DevDesignSystemPage />} />}

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
