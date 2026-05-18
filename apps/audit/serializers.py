from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    actor_id = serializers.IntegerField(source="actor.id", read_only=True, allow_null=True)
    actor_username = serializers.CharField(source="actor.username", read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "organization_id",
            "actor_id",
            "actor_username",
            "action",
            "entity_type",
            "entity_id",
            "before_data",
            "after_data",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        )
