# Architecture Decision Records

One file per meaningful architectural decision, numbered sequentially,
never renumbered or deleted — if a decision is later reversed, add a new
ADR that supersedes it and says so, rather than editing history.

| # | Title | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith, not microservices | Accepted |
| [0002](0002-custom-user-model.md) | Custom user model, introduced now | Accepted |
| [0003](0003-cors-configuration.md) | CORS via an explicit origin allowlist, not a wildcard | Accepted |

## Template

```md
# ADR-000N: Title

Status: Proposed / Accepted / Superseded by ADR-000M
Date: YYYY-MM-DD

## Context
What problem/decision is being made, and what constraints apply.

## Decision
What was decided.

## Consequences
What this makes easier, what it makes harder, what it forecloses.

## Alternatives considered
What else was on the table and why it wasn't chosen.
```
