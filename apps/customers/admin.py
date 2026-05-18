from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "first_name",
        "last_name",
        "phone",
        "organization",
        "is_active",
        "created_at",
    )
    list_filter = ("organization", "is_active")
    search_fields = ("reference", "first_name", "last_name", "phone", "email")
