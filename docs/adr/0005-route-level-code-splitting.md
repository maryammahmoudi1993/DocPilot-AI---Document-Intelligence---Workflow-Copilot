# ADR-0005: Route-level code splitting for every authenticated page

Status: Accepted
Date: 2026-08-12

## Context

By Phase 9, `App.tsx` statically imported all thirteen page components
(Dashboard, Documents, Review Queue, Document Review, AI Assistant,
Workflow Builder, Approvals, Analytics, Audit Log, Integrations,
Settings, plus Home/Sign In) at module top level. Two of those pages
pull in genuinely large third-party libraries — Workflow Builder uses
`@xyflow/react` (the graph editor canvas) and Analytics uses `recharts`
— and both landed in the single main JS chunk regardless of whether a
visitor ever opened those pages. A production build at the start of
Phase 10 produced one 1.16 MB (351 KB gzipped) main chunk.

## Decision

Every page mounted under the authenticated `/app/*` tree is now loaded
via `React.lazy()` + `<Suspense>`, wrapped per-route in
`RouteErrorBoundary` (see that component's docstring for why it's
separate from the app-wide `ErrorBoundary`). `Home` and `SignIn` stay
statically imported — they're needed for the very first paint of an
unauthenticated visit and are small.

Pages keep their existing named-export convention (`export function
DashboardPage()`, matching every other component in the codebase)
rather than switching to `export default` just to satisfy `lazy()`'s
calling convention — a small `pick()` adapter in `App.tsx` bridges the
two.

## Consequences

**Easier:** a visitor who never opens Workflow Builder or Analytics
never downloads their dependencies. Measured at the same commit:

| Chunk | Before | After |
| --- | --- | --- |
| Main (`index-*.js`) | 1,163 KB (351 KB gzip) | 454 KB (143 KB gzip) |
| Analytics (own chunk, recharts) | — (in main) | 358 KB (102 KB gzip) |
| Workflow Builder (own chunk, @xyflow/react) | — (in main) | 188 KB (59 KB gzip) |

Re-check this table (`npm run build`) whenever a route's dependencies
change materially — it's a budget to keep honest, not a one-time
number.

**Harder:** navigating to a not-yet-visited route now shows a brief
loading spinner (`FullPageSpinner`) instead of an instant transition —
an accepted, standard trade-off for code-split routes, and one Suspense
boundary per route keeps that flash scoped to the page being entered,
not the whole shell.

## Alternatives considered

**Manual `rollupOptions.output.manualChunks`**: could group the same
heavy dependencies into named vendor chunks without changing how pages
are imported. Rejected as strictly worse here — it still ships those
chunks to every visitor upfront (just as a separate `<script>` tag,
not entangled with `index.js`), whereas route-level `lazy()` only
fetches them when the route is actually entered.

**Preloading likely-next routes on hover/idle**: a reasonable follow-up
(React Router supports `<Link>` prefetch patterns), not implemented
here — out of scope for what this phase needed to demonstrate.
