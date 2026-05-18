from django.contrib import admin

from apps.catalog.models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "expected_amount", "currency", "is_active")
    list_filter = ("organization", "currency", "is_active")
    search_fields = ("name", "description")
