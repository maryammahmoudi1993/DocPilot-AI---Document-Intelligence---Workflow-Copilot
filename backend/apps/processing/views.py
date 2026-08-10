"""Minimum scaffold only — apps/documents/urls.py imports these names so
existing document tests keep passing on this test-first branch (an
ImportError here would otherwise break Django's URLconf loading for
every view-level test in the project, not just the new processing
ones). Real behavior lands on the feature branch; see
apps/processing/tests/test_views.py for the behavior these must satisfy.
"""

from rest_framework.views import APIView


class DocumentProcessingStatusView(APIView):
    def get(self, request, workspace_id, document_id):
        raise NotImplementedError


class DocumentProcessingRetryView(APIView):
    def post(self, request, workspace_id, document_id):
        raise NotImplementedError
