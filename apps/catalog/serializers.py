from rest_framework import serializers

from apps.catalog.models import Service


class ServiceSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "organization_id",
            "name",
            "description",
            "expected_amount",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "organization_id", "is_active", "created_at", "updated_at")


class ServiceDeactivateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(read_only=True, default=False)
