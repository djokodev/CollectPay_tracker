from django.db.models import QuerySet

from apps.organizations.models import OrganizationMembership


def get_user_organization_ids(user):
    if not user or not user.is_authenticated:
        return []

    return list(
        OrganizationMembership.objects.filter(user=user, is_active=True).values_list(
            "organization_id", flat=True
        )
    )


def resolve_request_organization_id(request):
    user = request.user
    if not user or not user.is_authenticated:
        return None

    requested = (
        request.query_params.get("organization_id")
        or request.headers.get("X-Organization-Id")
        or getattr(getattr(user, "account_profile", None), "active_organization_id", None)
    )

    allowed_ids = set(get_user_organization_ids(user))
    if not allowed_ids:
        return None

    if requested:
        try:
            requested_id = int(requested)
        except (TypeError, ValueError):
            return None
        if requested_id in allowed_ids:
            return requested_id

    return sorted(allowed_ids)[0]


class OrganizationScopedQuerysetMixin:
    organization_field = "organization"

    def get_user_organization_ids(self):
        return get_user_organization_ids(self.request.user)

    def scope_queryset(self, queryset: QuerySet):
        org_ids = self.get_user_organization_ids()
        filter_key = f"{self.organization_field}_id__in"
        return queryset.filter(**{filter_key: org_ids})
