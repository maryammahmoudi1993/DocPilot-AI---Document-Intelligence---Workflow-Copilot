"""Action-execution provider abstractions (project rule: mock external
providers at module boundaries). Every action kind's real side effect —
sending a notification, calling a webhook — goes through one of these
so unit tests never make a real network call. `MockActionProvider` is
the only one wired by default (see settings.WORKFLOW_ACTION_PROVIDER);
`HttpActionProvider` exists for a real deployment but uses only the
standard library (no new dependency to justify) and is never exercised
in tests."""

import json
import urllib.error
import urllib.request
from typing import Protocol


class ActionProviderError(Exception):
    """Normalized failure for a retryable action side effect (timeout,
    non-2xx response). Only raised for RETRYABLE_ACTION_KINDS."""


class ActionProvider(Protocol):
    def send_notification(self, *, message: str, recipient: str) -> dict: ...

    def trigger_webhook(self, *, url: str, payload: dict) -> dict: ...


class MockActionProvider:
    """Deterministic — records what *would* have been sent without any
    network call. Same input always yields the same recorded output,
    which is what makes workflow execution deterministic and safe for
    unit tests (project rule: no paid/external provider calls in
    tests)."""

    def send_notification(self, *, message: str, recipient: str) -> dict:
        return {"delivered": True, "channel": "mock", "recipient": recipient}

    def trigger_webhook(self, *, url: str, payload: dict) -> dict:
        return {"delivered": True, "url": url, "status_code": 200}


class HttpActionProvider:
    """Real implementation for a deployed environment — stdlib-only
    (urllib), no new dependency. Not covered by unit tests (would
    violate the no-external-calls-in-tests rule); exists so
    settings.WORKFLOW_ACTION_PROVIDER=http is a real, working option,
    not just a placeholder."""

    def send_notification(self, *, message: str, recipient: str) -> dict:
        # No real notification channel (email/Slack) is configured for
        # this portfolio project — logging is the honest "real" behavior
        # until one is. Never raises: a missing channel isn't a
        # retryable failure.
        import logging

        logging.getLogger(__name__).info(
            "workflow_notification", extra={"recipient": recipient, "message_length": len(message)}
        )
        return {"delivered": True, "channel": "log", "recipient": recipient}

    def trigger_webhook(self, *, url: str, payload: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                return {"delivered": True, "url": url, "status_code": response.status}
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ActionProviderError(str(exc)) from exc


def get_action_provider() -> ActionProvider:
    from django.conf import settings

    if settings.WORKFLOW_ACTION_PROVIDER == "http":
        return HttpActionProvider()
    return MockActionProvider()
