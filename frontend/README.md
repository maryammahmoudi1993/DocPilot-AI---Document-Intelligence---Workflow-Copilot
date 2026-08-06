# DocPilot AI — Frontend

React + TypeScript + Vite frontend application. See the repository root `CLAUDE.md` (local-only) for broader project context.

## Requirements

- Node.js 18+ (LTS recommended)
- npm 9+

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # then fill in real values
```

### Windows: `npm run <script>` fails with `'Workflow' is not recognized...`

This happens only if your checkout path contains an unescaped `&` (for
example a parent folder literally named `...Intelligence & Workflow...`) —
`npm.cmd`'s batch-file argument parsing splits the command at the `&`.
Fix it locally, once, without committing anything:

```bash
npm config set script-shell "C:\\Program Files\\Git\\bin\\bash.exe"
```

or create an untracked `frontend/.npmrc` with `script-shell=<path to
bash.exe>` (already gitignored — see root `.gitignore` — because the path
is machine-specific and would break Linux/Mac/CI if committed). Not needed
on macOS/Linux or in CI.

## Common commands

```bash
npm run dev            # Start development server
npm run build          # Build for production
npm run preview        # Preview production build
npm run lint           # Run ESLint
npm run lint:fix       # Fix ESLint issues
npm run typecheck      # Run TypeScript type checking
npm run format         # Format code with Prettier
npm run format:check   # Check formatting
npm run test           # Run unit tests with Vitest
npm run test:watch     # Run tests in watch mode
npm run test:coverage  # Run tests with coverage
npm run test:e2e       # Run end-to-end tests with Playwright
npm run test:e2e:ui    # Run E2E tests with UI
```

## Project structure

```
frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/         # Route-level page components
│   ├── lib/           # Utility libraries and API client
│   ├── test/          # Test setup and utilities
│   ├── config.ts      # Environment configuration
│   ├── App.tsx        # Root application component
│   └── main.tsx       # Application entry point
├── e2e/               # End-to-end tests
├── public/            # Static assets
├── index.html         # HTML entry point
├── vite.config.ts     # Vite configuration
├── vitest.config.ts   # Vitest configuration
├── playwright.config.ts # Playwright configuration
├── tailwind.config.js # Tailwind CSS configuration
├── tsconfig.json      # TypeScript configuration
└── package.json       # Dependencies and scripts
```

## Design system

`src/components/ui/` — reusable, unstyled-business-logic primitives (Button,
Input, Select, Tabs, Dialog, Drawer, Toast, StatusBadge, ConfidenceBadge,
MetricCard, EmptyState, ErrorState, Skeleton, DataTable shell, FilterBar,
ConfirmationDialog). `src/components/layout/` — the shared application
shell (AppShell, Sidebar, Header, PageHeader) every `/app/*` route renders
through; no page re-implements sidebar/header markup.

Design tokens (colors, radii, shadows, motion durations, z-index) live in
`tailwind.config.js`'s `theme.extend` and are consumed as Tailwind
utility classes (`bg-primary`, `rounded-lg`, `shadow-md`, `duration-fast`,
`z-modal`, …) rather than inline styles or repeated hex values.

Run `npm run dev` and visit `/dev/design-system` for a live reference of
every component (dev-only route — stripped from production builds via an
`import.meta.env.DEV` guard in `App.tsx`).

Built on [Radix UI](https://www.radix-ui.com/) primitives for Dialog,
Drawer, Select, Tabs, and Toast — they provide correct keyboard
navigation and ARIA roles out of the box. One caveat found while building
this: Radix's own focus-*restoration* on dialog close was unreliable
under jsdom (worked in real browsers, not in the Vitest test
environment) regardless of how the dialog was closed, so `Dialog`/`Drawer`
re-implement it explicitly (see the comment in `Dialog.tsx`) rather than
relying on it silently.

**Tailwind v4 gotcha**: a JS `tailwind.config.js` is ignored by Tailwind
v4 unless referenced via `@config "../tailwind.config.js";` in the CSS
entry point (`src/index.css`) — v4's default is a CSS-native `@theme`
block instead. Without it, every custom-token utility (and, separately,
every responsive `sm:`/`md:`/`lg:` variant — which needed `@import
"tailwindcss";` rather than the legacy `@tailwind base/components/utilities;`
directives) silently compiled to nothing. If you ever see a custom color
or breakpoint variant have no visual effect, check both of these first.

## Testing

### Unit Tests (Vitest)
- Located in `src/test/` directory
- Run with `npm run test`
- Coverage reports with `npm run test:coverage`

### End-to-End Tests (Playwright)
- Located in `e2e/` directory
- Run with `npm run test:e2e`
- Interactive UI mode with `npm run test:e2e:ui`
- Browsers: Chromium (configured)

## Environment Variables

See `.env.example` for required environment variables:

- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8000/api`)
- `VITE_APP_ENV`: Application environment (default: `development`)

## Code Quality

- **ESLint**: Configured with TypeScript and React rules
- **Prettier**: Automatic code formatting
- **TypeScript**: Strict mode enabled
- **Testing**: Unit tests with Vitest + React Testing Library, E2E with Playwright
