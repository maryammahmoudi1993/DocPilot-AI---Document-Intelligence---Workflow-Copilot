from rest_framework import status
from rest_framework.exceptions import APIException


class ApprovalError(APIException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code = "approval_error"
    default_detail = "This approval request could not be processed."


class InvalidApprovalTransitionError(ApprovalError):
    default_code = "invalid_approval_transition"
    default_detail = "This approval decision is not allowed from the current state."
