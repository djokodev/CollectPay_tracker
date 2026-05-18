from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from apps.payments.models import PaymentTransactionStatus
from apps.receipts.models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    payment_request_id = serializers.IntegerField(source="payment_request.id", read_only=True)
    transaction_id = serializers.IntegerField(source="transaction.id", read_only=True, allow_null=True)
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id",
            "organization_id",
            "payment_request_id",
            "transaction_id",
            "receipt_number",
            "public_reference",
            "amount_paid",
            "currency",
            "payment_status_snapshot",
            "customer_name",
            "service_name",
            "issued_at",
            "created_at",
            "verification_url",
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_verification_url(self, obj):
        return f"/api/receipts/verify/{obj.public_reference}/"


class GenerateReceiptSerializer(serializers.Serializer):
    payment_request_id = serializers.IntegerField()
    transaction_id = serializers.IntegerField(required=False)


class ReceiptVerificationSerializer(serializers.Serializer):
    receipt_number = serializers.CharField()
    public_reference = serializers.UUIDField()
    is_valid = serializers.BooleanField()
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    customer_name = serializers.CharField()
    service_name = serializers.CharField()
    issued_at = serializers.DateTimeField()


class _TransactionStatusCheckSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PaymentTransactionStatus.choices)
