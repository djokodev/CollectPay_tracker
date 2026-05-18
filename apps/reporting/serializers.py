from rest_framework import serializers

from apps.payments.models import PaymentRequestStatus


class DashboardMetricsQuerySerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False, min_value=1)
    service_id = serializers.IntegerField(required=False, min_value=1)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "La date de fin doit etre superieure ou egale a la date de debut."}
            )
        return attrs


class PaymentRequestExportQuerySerializer(serializers.Serializer):
    export_format = serializers.ChoiceField(choices=("csv", "xlsx", "pdf"), default="csv")
    status = serializers.ChoiceField(
        choices=PaymentRequestStatus.choices,
        required=False,
    )
    customer_id = serializers.IntegerField(required=False, min_value=1)
    service_id = serializers.IntegerField(required=False, min_value=1)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "La date de fin doit etre superieure ou egale a la date de debut."}
            )
        return attrs
