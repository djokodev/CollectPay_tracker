from django.contrib import admin

from apps.payments.models import PaymentRequest


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
