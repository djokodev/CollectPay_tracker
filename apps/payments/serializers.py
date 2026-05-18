from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.payments.models import PaymentRequest, PaymentRequestStatus


class PaymentRequestSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    customer_id = serializers.IntegerField(source="customer.id", read_only=True)
    service_id = serializers.IntegerField(source="service.id", read_only=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), write_only=True)
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), write_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PaymentRequest
        fields = (
            "id",
            "organization_id",
            "reference",
            "customer",
            "customer_id",
            "customer_name",
            "service",
            "service_id",
            "service_name",
            "expected_amount",
            "paid_amount",
            "remaining_amount",
            "status",
            "due_date",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization_id",
            "reference",
            "customer",
            "service",
            "paid_amount",
            "remaining_amount",
            "status",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        organization_id = self.context["organization_id"]

        customer = attrs["customer"]
        service = attrs["service"]

        if customer.organization_id != organization_id:
            raise serializers.ValidationError("Le client ne correspond pas a l'organisation active.")
        if service.organization_id != organization_id:
            raise serializers.ValidationError("Le service ne correspond pas a l'organisation active.")

        if request.method in {"POST", "PUT", "PATCH"} and attrs.get("expected_amount"):
            if attrs["expected_amount"] <= Decimal("0.00"):
                raise serializers.ValidationError("Le montant attendu doit etre superieur a 0.")

        return attrs


class PaymentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PaymentRequestStatus.choices)


class PaymentManualAmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class CancelPaymentRequestSerializer(serializers.Serializer):
    pass
