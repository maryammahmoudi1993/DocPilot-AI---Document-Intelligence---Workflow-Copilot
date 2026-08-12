"""Stable, safe-to-serialize errors for the extraction/review API. Views
translate these into the project's standard error envelope (see
common.exceptions) rather than letting a raw exception leak."""

from rest_framework import status
from rest_framework.exceptions import APIException


class ExtractionError(APIException):
    # Typed as plain `int` (not inferred as Literal[400]) so subclasses
    # (e.g. StaleVersionError below) can override it with a different
    # HTTP status without mypy treating that as incompatible.
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code = "extraction_error"
    default_detail = "The extraction could not be processed."


class StaleVersionError(ExtractionError):
    """Raised when a correction or transition request's `expected_version`
    no longer matches the row — i.e. someone else changed it first."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "stale_version"
    default_detail = "This extraction was changed by someone else. Reload and try again."


class InvalidTransitionError(ExtractionError):
    default_code = "invalid_transition"
    default_detail = "This status change is not allowed from the current state."


class ExtractionLockedError(ExtractionError):
    """A correction was attempted on an extraction that is no longer
    editable (already approved or rejected)."""

    default_code = "extraction_locked"
    default_detail = "This extraction is no longer editable."
