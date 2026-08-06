from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.health.services import get_readiness_statuses


class HealthView(APIView):
    """Liveness probe: process is up and able to serve requests.

    Deliberately does not check any dependency — a dependency outage
    should surface on `/api/readiness/`, not make the liveness probe fail
    and cause an orchestrator to restart a perfectly healthy process.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict}, description="Liveness probe.")
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    """Readiness probe: process is up *and* its dependencies are reachable."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict, 503: dict}, description="Readiness probe.")
    def get(self, request: Request) -> Response:
        statuses = get_readiness_statuses()
        all_ok = all(status.ok for status in statuses)
        payload = {
            "status": "ok" if all_ok else "unavailable",
            "checks": {status.name: {"ok": status.ok} for status in statuses},
        }
        return Response(payload, status=200 if all_ok else 503)
