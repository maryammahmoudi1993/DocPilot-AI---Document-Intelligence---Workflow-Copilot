"""Normalized processing-pipeline exceptions. Every failure the pipeline
(pipeline.py) can raise carries a stable, safe-to-display `code` and an
explicit `retryable` flag — the orchestrator (tasks.py) branches on
those, never on exception message text, and never persists a raw
exception message/traceback onto the job (see ProcessingJob.error_message).
"""


class ProcessingError(Exception):
    code = "internal_error"
    retryable = False

    def __init__(self, message: str, *, code: str | None = None, retryable: bool | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable


class ValidationProcessingError(ProcessingError):
    """Not retryable — retrying a corrupt or password-protected file
    produces the same failure every time."""

    retryable = False


class RetryableProcessingError(ProcessingError):
    """A transient failure (provider timeout, provider unavailable) that
    might succeed on a later attempt."""

    retryable = True
