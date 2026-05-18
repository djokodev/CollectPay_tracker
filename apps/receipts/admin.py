from django.contrib import admin

from apps.receipts.models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "organization",
        "payment_request",
        "amount_paid",
        "currency",
        "issued_at",
    )
    list_filter = ("organization", "currency")
    search_fields = (
        "receipt_number",
        "payment_request__reference",
        "customer_name",
        "service_name",
    )
