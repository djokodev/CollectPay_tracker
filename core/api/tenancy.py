from django.db.models import QuerySet

from apps.organizations.models import OrganizationMembership


class OrganizationScopedQuerysetMixin:
    organization_field = "organization"

    def get_user_organization_ids(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return []

        return list(
            OrganizationMembership.objects.filter(user=user, is_active=True).values_list(
                "organization_id", flat=True
            )
        )

    def scope_queryset(self, queryset: QuerySet):
        org_ids = self.get_user_organization_ids()
        filter_key = f"{self.organization_field}_id__in"
        return queryset.filter(**{filter_key: org_ids})
