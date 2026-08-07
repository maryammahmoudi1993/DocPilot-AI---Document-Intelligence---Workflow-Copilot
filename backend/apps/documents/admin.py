from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["filename", "workspace", "status", "size_bytes", "created_at"]
    list_filter = ["status", "content_type"]
    search_fields = ["filename", "workspace__name", "checksum_sha256"]
    readonly_fields = ["checksum_sha256", "storage_key", "created_at", "archived_at"]
