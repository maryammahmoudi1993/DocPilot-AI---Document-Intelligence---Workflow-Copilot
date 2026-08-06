from django.contrib import admin

from apps.workspaces.models import Workspace, WorkspaceMembership


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ["workspace", "user", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["workspace__name", "user__email"]
