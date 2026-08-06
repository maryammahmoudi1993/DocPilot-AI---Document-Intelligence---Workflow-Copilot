from datetime import timedelta
from typing import cast

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    ActiveWorkspaceSerializer,
    LoginSerializer,
    SessionSerializer,
    UserSerializer,
)
from apps.accounts.services import authenticate_user
from apps.audit.services import record_event
from apps.workspaces.models import WorkspaceMembership
from apps.workspaces.services import set_active_workspace

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    refresh_lifetime = cast(timedelta, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(refresh_lifetime.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


class LoginView(APIView):
    """Sets the refresh token as an httpOnly cookie (never readable by
    frontend JS — see the project rule against storing long-lived
    secrets in insecure browser storage) and returns a short-lived access
    token in the body for in-memory frontend storage."""

    permission_classes = [AllowAny]
    throttle_scope = "auth-login"

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(request=request, **serializer.validated_data)

        refresh = RefreshToken.for_user(user)
        response = Response(
            {"access": str(refresh.access_token), "user": UserSerializer(user).data}
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class RefreshView(APIView):
    """Reads the refresh token from the httpOnly cookie (never the
    request body) and, per SIMPLE_JWT's ROTATE_REFRESH_TOKENS /
    BLACKLIST_AFTER_ROTATION settings, rotates it — the old refresh token
    stops working the moment a new one is issued."""

    permission_classes = [AllowAny]
    throttle_scope = "auth-refresh"

    @extend_schema(request=None, responses={200: dict})
    def post(self, request: Request) -> Response:
        raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_token:
            raise AuthenticationFailed("No refresh token provided.")

        serializer = TokenRefreshSerializer(data={"refresh": raw_token})
        serializer.is_valid(raise_exception=True)

        response = Response({"access": serializer.validated_data["access"]})
        new_refresh = serializer.validated_data.get("refresh")
        if new_refresh:
            _set_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()  # type: ignore[arg-type]
            except TokenError:
                pass  # already invalid/expired — nothing left to blacklist

        # IsAuthenticated guarantees a real User here, not AnonymousUser.
        record_event(event_type="auth.logout", actor=cast(User, request.user))

        response = Response(status=204)
        response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
        return response


class SessionView(APIView):
    """Session bootstrap: current user, every workspace they belong to
    (with their role in each), and their active-workspace pointer."""

    @extend_schema(responses={200: SessionSerializer})
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)  # IsAuthenticated guarantees this
        memberships = WorkspaceMembership.objects.filter(user=user).select_related("workspace")
        data = {
            "user": user,
            "workspaces": list(memberships),
            "active_workspace_id": user.active_workspace_id,
        }
        return Response(SessionSerializer(data).data)


class ActiveWorkspaceView(APIView):
    @extend_schema(request=ActiveWorkspaceSerializer, responses={204: None})
    def patch(self, request: Request) -> Response:
        serializer = ActiveWorkspaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # set_active_workspace re-validates real membership — a forged
        # workspace_id for a workspace the user doesn't belong to is
        # rejected here, not trusted.
        set_active_workspace(
            user=cast(User, request.user),  # IsAuthenticated guarantees this
            workspace_id=serializer.validated_data["workspace_id"],
        )
        return Response(status=204)
