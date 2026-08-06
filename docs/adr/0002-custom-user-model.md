# ADR-0002: Custom user model, introduced now

Status: Accepted
Date: 2026-08-06

## Context

Django's official recommendation is: always use a custom user model for
any new project, and do it *before* the first `migrate` — swapping
`AUTH_USER_MODEL` after real data exists in `django.contrib.auth.User`
requires a nontrivial, error-prone data migration. This project had no
migration ever applied to a real database (verified: `manage.py migrate`
had never been run against a persisted database in this repository's
history — see `docs/repository-audit.md`), so this was the safe window.

## Decision

`apps.accounts.User` extends `AbstractUser`, adds a unique `email` field
used as `USERNAME_FIELD` (this project logs in by email, not a separate
username), and a nullable `active_workspace` FK (UX convenience pointer
only — see ADR discussion in `apps/workspaces/permissions.py`'s module
docstring for why it's never an authorization source).

## Consequences

**Easier:** email-based login without a workaround; room to add
project-specific user fields later without a disruptive migration.

**Harder:** `username` is still present (inherited from `AbstractUser`,
kept for Django admin/internals compatibility) but functionally unused —
`User.save()` defaults it to the email on every creation path (manager,
`get_or_create`, factory, admin) so it never blocks on its own unique
constraint. A model with less baggage would drop `username` entirely by
building on `AbstractBaseUser` instead of `AbstractUser`; `AbstractUser`
was chosen for compatibility with `django.contrib.admin` and other
`contrib` code that assumes it.

## Alternatives considered

**`AbstractBaseUser` from scratch** (no `username` field at all):
rejected for this phase — more correct long-term, but more code to get
right (permissions mixins, admin integration) for marginal benefit at
this project's current stage. Revisit if `username`'s presence ever
causes real friction beyond the save()-time default already handling it.

**Keep `django.contrib.auth.User`, login by username**: rejected — email
login is the realistic modern UX for this product, and retrofitting a
custom user model later (after real data exists) is the exact problem
this ADR exists to avoid.
