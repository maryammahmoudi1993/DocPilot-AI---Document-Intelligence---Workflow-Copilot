"""Stable, safe-to-serialize errors for the assistant API — see
common.exceptions for how these become the standard error envelope."""

from rest_framework import status
from rest_framework.exceptions import APIException


class AssistantError(APIException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code = "assistant_error"
    default_detail = "The question could not be answered."


class InvalidDocumentScopeAPIError(AssistantError):
    default_code = "invalid_document_scope"
    default_detail = "One or more selected documents don't exist in this workspace."


class ProviderUnavailableAPIError(AssistantError):
    """The embedding/generation provider failed (timeout, rate limit,
    outage) — a stable, safe-to-display code instead of a leaked
    internal exception. Retryable from the caller's perspective (ask
    again), unlike a validation error."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "provider_unavailable"
    default_detail = "The assistant is temporarily unavailable. Please try again."
