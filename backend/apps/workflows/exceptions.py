"""Stable, safe-to-serialize errors for the workflow API — see
common.exceptions for how these become the standard error envelope."""

from rest_framework import status
from rest_framework.exceptions import APIException


class WorkflowError(APIException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code = "workflow_error"
    default_detail = "The workflow request could not be completed."


class InvalidGraphError(WorkflowError):
    default_code = "invalid_graph"
    default_detail = "This workflow graph is not valid."


class VersionImmutableError(WorkflowError):
    """Raised when an edit is attempted against an activated (or
    archived) version — activated versions are immutable by design; a
    caller wanting to change one must create a new draft version."""

    default_code = "version_immutable"
    default_detail = "This workflow version can no longer be edited."
