from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "entity_type", "entity_id", "organization", "actor")
    list_filter = ("action", "entity_type", "organization")
    search_fields = ("entity_id", "action", "entity_type", "actor__username")
