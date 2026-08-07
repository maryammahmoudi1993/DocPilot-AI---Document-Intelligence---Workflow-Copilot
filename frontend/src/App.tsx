import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider } from './components/ui/Toast';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { RequireRole } from './components/auth/RequireRole';
import { MANAGER_ROLES } from './features/auth/types';
import { Home } from './pages/Home';
import { NotFound } from './pages/NotFound';
import { SignInPage } from './pages/SignIn';
import { AccessDeniedPage } from './pages/AccessDenied';
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Session/workspace data changes rarely within a single visit;
      // avoid a network round trip on every focus/mount.
      staleTime: 30_000,
      retry: false,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/sign-in" element={<SignInPage />} />
              <Route path="/access-denied" element={<AccessDeniedPage />} />

              {/* Every /app/* route renders through AppShell (single
                  shared shell) and requires a real session — client-side
                  gating is UX only, the backend enforces authorization
                  independently on every request (see ProtectedRoute). */}
              <Route element={<ProtectedRoute />}>
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
                  <Route element={<RequireRole allowedRoles={MANAGER_ROLES} />}>
                    <Route path="settings" element={<SettingsPage />} />
                  </Route>
                </Route>
              </Route>

              {/* Never present in a production build — see the DEV guard. */}
              {import.meta.env.DEV && (
                <Route path="/dev/design-system" element={<DevDesignSystemPage />} />
              )}

              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
