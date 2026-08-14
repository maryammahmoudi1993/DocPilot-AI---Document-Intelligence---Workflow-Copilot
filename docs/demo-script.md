# Demo Script (60–90 seconds)

A guided walkthrough of the primary flow. Assumes
`docker compose up`, `seed_demo_data`, and `seed_demo_documents` have
already run (see the root [`README.md`](../README.md)) and the frontend
dev server is running.

| Time | Action | What it shows |
|---|---|---|
| 0:00–0:08 | Land on `/` (marketing page), click through to `/sign-in`, sign in as `reviewer@demo.docpilot.ai` (password printed by `seed_demo_data`). | Honest landing page — no fabricated logos/testimonials — real JWT sign-in, not a mocked session. |
| 0:08–0:18 | `/app/dashboard` — real metric cards and a recent-documents list. | Operational data pulled from the actual API, not hardcoded. |
| 0:18–0:28 | `/app/documents` — the pre-seeded `sample-invoice.pdf` is already listed with a completed processing status. | Async pipeline already ran: digital-text extraction → classification → structured extraction, all before this screen loads. |
| 0:28–0:42 | `/app/review-queue` — open the invoice, show a low-confidence field (illustratively flagged), correct it, save. | Confidence-aware human review with a real correction recorded, not a static mock screen. |
| 0:42–0:52 | `/app/approvals` — approve the document (confirmation dialog, then the approve action). | Idempotent approval decision, audit event recorded. |
| 0:52–1:05 | `/app/assistant` — ask "What's the total on the sample invoice?" — the answer arrives with a citation back to the source chunk. | Grounded RAG, not a free-floating chat answer (mock LLM provider — see `docs/limitations.md`). |
| 1:05–1:15 | `/app/workflows` — open the example approval workflow, show the webhook/notification action node. | Visual workflow builder (React Flow), not a config file. |
| 1:15–1:22 | `/app/integrations` — show the delivery log entry for the webhook that just fired, labeled "Simulated integration". | Signed, idempotent webhook delivery, honestly labeled as simulated (no real third-party endpoint). |
| 1:22–1:28 | `/app/audit-log` — filter to the last few minutes, expand one event's JSON detail. | Immutable, filterable audit trail covering every step just performed. |
| 1:28–1:30 | Back to `/app/analytics` — the review-rate / workflow-success metrics reflect the actions just taken. | Real aggregation over the same rows, not a separately-maintained dashboard. |

## Recording notes

- Use the `Demo Workspace` seeded by `seed_demo_data` — never a
  workspace with real data.
- If recording video, mute/crop the browser address bar showing
  `localhost` only if a public-facing recording is the goal; otherwise
  it's fine to show — nothing in the URL bar exposes a secret.
- Re-run `python manage.py reset_demo_data` between recordings for a
  clean, repeatable state.
