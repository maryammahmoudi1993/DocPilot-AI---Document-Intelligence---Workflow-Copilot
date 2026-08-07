from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.documents.models import Document
from apps.documents.services import get_document_signed_url


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "content_type",
            "size_bytes",
            "checksum_sha256",
            "status",
            "uploaded_by",
            "created_at",
            "archived_at",
        ]
        read_only_fields = fields


class DocumentDetailSerializer(DocumentSerializer):
    # Generated fresh on every request — never stored/cached, and expires
    # per DOCUMENT_SIGNED_URL_EXPIRY_SECONDS (see storage.py).
    download_url = serializers.SerializerMethodField()

    class Meta(DocumentSerializer.Meta):
        fields = [*DocumentSerializer.Meta.fields, "download_url"]
        read_only_fields = fields

    def get_download_url(self, document: Document) -> str:
        return get_document_signed_url(document=document)


class BulkActionSerializer(serializers.Serializer):
    document_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, min_length=1
    )
