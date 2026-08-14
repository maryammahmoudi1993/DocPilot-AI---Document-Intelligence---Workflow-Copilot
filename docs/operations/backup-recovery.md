# Backup & Recovery

What needs backing up, and the recovery process, for a deployment of
this project.

## What holds state

| Store | Contents | Backup approach |
|---|---|---|
| PostgreSQL | Everything except file bytes: users, workspaces, documents metadata, extraction/approval/workflow/audit/notification rows, webhook config (secrets encrypted) | `pg_dump`/continuous WAL archiving, per your host's managed-Postgres offering or a self-managed schedule |
| Object storage (S3-compatible / MinIO) | Uploaded document files | Bucket versioning + cross-region replication (real S3) or volume snapshots (self-hosted MinIO) |
| Redis | Cache + Celery broker/result backend — no durable application state that isn't reconstructable | Not backed up; losing it loses in-flight Celery task state and cached values only, not committed application data |

Redis is intentionally excluded from the backup story: nothing in this
project treats Redis as a system of record. A Celery task interrupted by
Redis data loss is safe to re-enqueue (project rule: every task is
idempotent).

## Recommended schedule (for a real deployment — not automated in this repository)

- **PostgreSQL:** nightly full backup + continuous WAL archiving (point-
  in-time recovery), retained per your compliance/portfolio needs — 7–30
  days is a reasonable default for a project with no real regulatory
  retention requirement.
- **Object storage:** if using real S3, enable versioning and, if
  cross-region durability matters for your deployment, replication. If
  self-hosting MinIO, snapshot the underlying volume on the same
  schedule as the database (a document row referencing a file that no
  longer exists is a worse failure mode than a slightly stale database).

## Recovery process

1. **Restore PostgreSQL** from the most recent backup (or a specific
   point-in-time via WAL replay) into a fresh instance.
2. **Restore object storage** to a matching point in time — if using
   versioned S3, this can mean reverting individual objects; if using
   volume snapshots, restore the volume.
3. **Point the application at the restored instances** (`DATABASE_URL`,
   `DOCUMENT_STORAGE_*`) and run `python manage.py migrate --noinput` to
   confirm the schema matches the currently-deployed code version before
   routing traffic.
4. **Verify** with `GET /api/readiness/` and a manual check that a known
   document (from before the incident) is both listed and downloadable.
5. **Re-run `seed_demo_data`** only if this deployment serves the
   portfolio demo and the demo workspace was affected — never run it
   against a restore containing real non-demo data without confirming
   its idempotent `get_or_create` behavior is actually what you want
   (see `backend/apps/accounts/management/commands/seed_demo_data.py`).

## What this project does not provide

- No automated backup job is included in this repository (no
  `pg_dump` cron, no lifecycle policy applied by code here) — this
  document describes the process; wiring the actual schedule is a
  per-deployment infrastructure decision (managed-database backups are
  the common real-world choice and usually require no code here at
  all).
- No tested disaster-recovery drill has been run against a real restore
  for this portfolio project — see [`docs/limitations.md`](../limitations.md).
