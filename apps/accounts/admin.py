from django.contrib import admin

from apps.accounts.models import AccountProfile


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_active_member", "created_at")
    list_filter = ("role", "is_active_member")
    search_fields = ("user__username", "user__email", "phone")
