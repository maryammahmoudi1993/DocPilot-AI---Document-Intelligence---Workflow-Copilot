import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from '@/mocks/server';
import { setAccessToken } from '@/stores/authTokenStore';

// Every test hits the real API contract shape via MSW rather than
// hand-mocked fetch — see src/mocks/handlers.ts. Unhandled requests
// error loudly instead of silently falling through to a real network
// call, so a missing handler is a visible test failure, not a flaky one.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  // The auth token store is a module-level singleton — without this, a
  // token set in one test would leak into the next.
  setAccessToken(null);
});
afterAll(() => server.close());

// jsdom doesn't implement the Pointer Events capture API or
// scrollIntoView. Radix UI primitives (Toast, Select, Dialog swipe/drag
// handling) call these unconditionally, so every test using them throws
// without this polyfill — a standard, widely-documented Radix+jsdom
// workaround, not something specific to this project's components.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

// jsdom has no real layout engine, so it doesn't implement matchMedia
// either — components using useMediaQuery (e.g. DocumentReviewPage's
// split/tabbed responsive layout) need a callable stand-in. Defaults to
// "no match" (narrow-viewport behavior); tests that care about the
// wide-viewport branch stub this per-test instead.
if (typeof window.matchMedia !== 'function') {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

// jsdom has no ResizeObserver (it's a real-layout-engine API) — the
// Workflow Builder's canvas (@xyflow/react) measures its container with
// one unconditionally and throws without this stub.
if (typeof window.ResizeObserver !== 'function') {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
