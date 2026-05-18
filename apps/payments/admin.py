from django.contrib import admin

from apps.payments.models import PaymentRequest, PaymentTransaction


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "organization",
        "customer",
        "service",
        "expected_amount",
        "paid_amount",
        "status",
        "due_date",
    )
    list_filter = ("organization", "status")
    search_fields = ("reference", "customer__first_name", "customer__last_name", "service__name")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_reference",
        "organization",
        "payment_request",
        "amount_received",
        "payment_method",
        "status",
        "paid_at",
    )
    list_filter = ("organization", "status", "payment_method")
    search_fields = ("transaction_reference", "payer_phone", "operator")
