import { Link } from 'react-router-dom';
import {
  BadgeCheck,
  Bot,
  CheckSquare,
  FileText,
  GitBranch,
  Sparkles,
  Workflow,
} from 'lucide-react';

const FEATURES = [
  {
    icon: FileText,
    title: 'Upload & process',
    description:
      'Drag in invoices, contracts, receipts, and forms. Digital PDFs parse instantly; scanned pages run through OCR automatically.',
  },
  {
    icon: Sparkles,
    title: 'Extract & validate',
    description:
      'Structured fields are extracted with confidence scores, flagged for review when they fall short, and corrected by a human when needed.',
  },
  {
    icon: Bot,
    title: 'Ask with citations',
    description:
      'A retrieval-grounded assistant answers questions about your documents and always points back to the source page.',
  },
  {
    icon: Workflow,
    title: 'Automate the next step',
    description:
      'Build no-code workflows that tag, notify, or trigger a webhook the moment a document reaches a given state.',
  },
  {
    icon: CheckSquare,
    title: 'Approve high-value actions',
    description:
      'Route risk-flagged requests to the right role, with a full audit trail of who decided what and when.',
  },
  {
    icon: GitBranch,
    title: 'Track everything',
    description:
      'An immutable audit log and real operational analytics — not sample numbers — show what actually happened.',
  },
];

const STEPS = [
  'Upload a document',
  'Background processing extracts structured data',
  'Low-confidence fields are flagged for review',
  'A reviewer corrects and approves it',
  'The document is indexed for grounded Q&A',
  'A workflow notifies the right person or system',
];

export function Home() {
  return (
    <div className="min-h-screen bg-card text-text-primary">
      <nav className="sticky top-0 z-sticky border-b border-border bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary">
              <FileText className="h-4 w-4 text-white" aria-hidden="true" />
            </div>
            <span className="text-lg font-extrabold tracking-tight">DocPilot AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/sign-in" className="px-4 py-2 text-sm font-semibold text-text-primary">
              Sign in
            </Link>
            <Link
              to="/sign-in"
              className="rounded-md bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors duration-fast hover:bg-primary-hover"
            >
              View the demo
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <header className="bg-gradient-to-b from-lavender to-card px-6 py-20">
          <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 lg:grid-cols-2">
            <div>
              <span className="mb-5 inline-flex items-center gap-1.5 rounded-full bg-primary-soft px-3.5 py-1.5 text-xs font-bold text-primary">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Portfolio demonstration
              </span>
              <h1 className="mb-5 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
                Turn documents into structured data, trusted answers, and automated actions.
              </h1>
              <p className="mb-8 max-w-lg text-lg leading-relaxed text-text-secondary">
                Upload invoices, contracts, forms, and reports. DocPilot AI extracts the
                information, flags what needs review, answers questions with citations, and
                automates the next step — a working modular-monolith reference build, not a
                production SaaS.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/sign-in"
                  className="rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-white shadow-lg transition-colors duration-fast hover:bg-primary-hover"
                >
                  Explore the demo workspace
                </Link>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-xl border border-border bg-card px-6 py-3.5 text-sm font-bold text-text-primary transition-colors duration-fast hover:border-primary"
                >
                  View source
                </a>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-5 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-soft">
                    <FileText className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  </div>
                  <span className="text-sm font-bold">Invoice_INV-1032.pdf</span>
                </div>
                <span className="rounded-full bg-status-review-bg px-2.5 py-1 text-xs font-bold text-status-review">
                  Needs review · 84%
                </span>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1.1fr_1fr]">
                <div className="h-48 rounded-lg bg-lavender p-3">
                  <div className="mb-2 h-2 w-3/5 rounded bg-border" />
                  <div className="mb-3 h-2 w-4/5 rounded bg-border" />
                  <div className="mb-2 h-9 w-full rounded border border-status-review bg-status-review-bg" />
                  <div className="mb-2 h-2 w-3/4 rounded bg-border" />
                  <div className="h-2 w-1/2 rounded bg-border" />
                </div>
                <div className="flex flex-col gap-2">
                  {[
                    { label: 'VENDOR', value: 'Acme Corp', confidence: '96%', good: true },
                    { label: 'TOTAL', value: '$7,150.00', confidence: '78%', good: false },
                    { label: 'DUE DATE', value: 'Jun 14, 2026', confidence: '99%', good: true },
                  ].map((field) => (
                    <div key={field.label} className="rounded-lg bg-lavender px-2.5 py-2">
                      <div className="text-[10px] font-semibold text-text-muted">{field.label}</div>
                      <div className="flex items-center justify-between text-xs font-bold">
                        {field.value}
                        <span
                          className={field.good ? 'text-status-approved' : 'text-status-review'}
                        >
                          {field.confidence}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </header>

        <section className="border-y border-border bg-lavender px-6 py-6 text-center">
          <p className="text-sm font-medium text-text-secondary">
            <BadgeCheck className="mr-1.5 inline h-4 w-4 text-primary" aria-hidden="true" />
            Sample data throughout — every screen is labeled honestly, not dressed up with
            fabricated customers or claims.
          </p>
        </section>

        <section className="px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <h2 className="mb-3 text-center text-3xl font-extrabold tracking-tight">
              One pipeline, from upload to action
            </h2>
            <p className="mx-auto mb-12 max-w-2xl text-center text-text-secondary">
              Every capability below is implemented and working end to end in this build.
            </p>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <div key={feature.title} className="rounded-xl border border-border bg-card p-6">
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft">
                    <feature.icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  </div>
                  <h3 className="mb-1.5 text-base font-bold">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-text-secondary">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-lavender px-6 py-20">
          <div className="mx-auto max-w-3xl">
            <h2 className="mb-8 text-center text-3xl font-extrabold tracking-tight">
              The demo flow
            </h2>
            <ol className="flex flex-col gap-3">
              {STEPS.map((step, index) => (
                <li key={step} className="flex items-center gap-4 rounded-xl bg-card p-4 shadow-sm">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-bold text-primary">
                    {index + 1}
                  </span>
                  <span className="text-sm font-medium text-text-primary">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="px-6 py-20 text-center">
          <div className="mx-auto max-w-xl">
            <h2 className="mb-4 text-3xl font-extrabold tracking-tight">See it for yourself</h2>
            <p className="mb-8 text-text-secondary">
              Sign in to a seeded demo workspace — no setup required.
            </p>
            <Link
              to="/sign-in"
              className="inline-block rounded-xl bg-primary px-8 py-3.5 text-sm font-bold text-white shadow-lg transition-colors duration-fast hover:bg-primary-hover"
            >
              Explore the demo workspace
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-8 text-center text-xs text-text-muted">
        DocPilot AI is a portfolio demonstration project. Metrics, workspaces, and documents shown
        are sample data.
      </footer>
    </div>
  );
}
