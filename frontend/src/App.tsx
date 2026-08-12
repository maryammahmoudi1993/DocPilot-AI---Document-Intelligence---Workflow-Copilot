import { lazy, Suspense, type ComponentType } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RouteErrorBoundary } from './components/RouteErrorBoundary';
import { ToastProvider } from './components/ui/Toast';
import { FullPageSpinner } from './components/ui/FullPageSpinner';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { RequireRole } from './components/auth/RequireRole';
import { MANAGER_ROLES } from './features/auth/types';
import { Home } from './pages/Home';
import { NotFound } from './pages/NotFound';
import { SignInPage } from './pages/SignIn';
import { AccessDeniedPage } from './pages/AccessDenied';
import { DevDesignSystemPage } from './pages/DevDesignSystem';

// Everything behind /app/* requires a signed-in session, so none of it
// is needed for the very first paint (landing/sign-in) — code-splitting
// these routes keeps the initial bundle to what an unauthenticated
// visitor actually needs. Two pages pull in genuinely heavy libraries
// (WorkflowBuilder → @xyflow/react, Analytics → recharts) that would
// otherwise sit in the main chunk for every visitor regardless of
// whether they ever open those pages.
const DashboardPage = lazy(() => import('./pages/Dashboard').then(pick('DashboardPage')));
const DocumentsPage = lazy(() => import('./pages/Documents').then(pick('DocumentsPage')));
const ReviewQueuePage = lazy(() => import('./pages/ReviewQueue').then(pick('ReviewQueuePage')));
const DocumentReviewPage = lazy(() =>
  import('./pages/DocumentReview').then(pick('DocumentReviewPage')),
);
const AiAssistantPage = lazy(() => import('./pages/AiAssistant').then(pick('AiAssistantPage')));
const WorkflowBuilderPage = lazy(() =>
  import('./pages/WorkflowBuilder').then(pick('WorkflowBuilderPage')),
);
const ApprovalsPage = lazy(() => import('./pages/Approvals').then(pick('ApprovalsPage')));
const AnalyticsPage = lazy(() => import('./pages/Analytics').then(pick('AnalyticsPage')));
const AuditLogPage = lazy(() => import('./pages/AuditLog').then(pick('AuditLogPage')));
const IntegrationsPage = lazy(() => import('./pages/Integrations').then(pick('IntegrationsPage')));
const SettingsPage = lazy(() => import('./pages/Settings').then(pick('SettingsPage')));

// react-router-dom's lazy-route convention expects a default export;
// this project's pages are all named exports (consistent with every
// other component in the codebase) — this tiny adapter avoids adding a
// `export default` to every page file just to satisfy `lazy()`.
function pick<K extends string, M extends Record<K, ComponentType>>(key: K) {
  return (module: M) => ({ default: module[key] });
}

/** Suspense fallback + a route-scoped error boundary (see
 * RouteErrorBoundary — distinct from the app-wide ErrorBoundary, which
 * would take out the sidebar too) around every lazy page. */
function LazyRoute({ Component }: { Component: ComponentType }) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<FullPageSpinner />}>
        <Component />
      </Suspense>
    </RouteErrorBoundary>
  );
}

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
                  <Route path="dashboard" element={<LazyRoute Component={DashboardPage} />} />
                  <Route path="documents" element={<LazyRoute Component={DocumentsPage} />} />
                  <Route
                    path="review-queue"
                    element={<LazyRoute Component={ReviewQueuePage} />}
                  />
                  <Route
                    path="documents/:documentId/review"
                    element={<LazyRoute Component={DocumentReviewPage} />}
                  />
                  <Route path="assistant" element={<LazyRoute Component={AiAssistantPage} />} />
                  <Route
                    path="workflows"
                    element={<LazyRoute Component={WorkflowBuilderPage} />}
                  />
                  <Route path="approvals" element={<LazyRoute Component={ApprovalsPage} />} />
                  <Route path="analytics" element={<LazyRoute Component={AnalyticsPage} />} />
                  <Route path="audit-log" element={<LazyRoute Component={AuditLogPage} />} />
                  <Route
                    path="integrations"
                    element={<LazyRoute Component={IntegrationsPage} />}
                  />
                  <Route element={<RequireRole allowedRoles={MANAGER_ROLES} />}>
                    <Route path="settings" element={<LazyRoute Component={SettingsPage} />} />
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
