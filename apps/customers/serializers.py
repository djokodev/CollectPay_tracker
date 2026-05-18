from rest_framework import serializers

from apps.customers.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "organization_id",
            "reference",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization_id",
            "reference",
            "full_name",
            "is_active",
            "created_at",
            "updated_at",
        )


class CustomerDeactivateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(read_only=True, default=False)


class CustomerHistorySerializer(serializers.Serializer):
    customer = CustomerSerializer()
    payment_requests = serializers.ListField(child=serializers.DictField(), default=list)
    transactions = serializers.ListField(child=serializers.DictField(), default=list)
