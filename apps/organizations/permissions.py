from rest_framework.permissions import BasePermission

from apps.organizations.models import OrganizationMembership, OrganizationRole


MANAGER_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MANAGER}


def get_membership(user, organization_id):
    if not user or not user.is_authenticated:
        return None

    return (
        OrganizationMembership.objects.filter(
            user=user,
            organization_id=organization_id,
            is_active=True,
        )
        .select_related("organization")
        .first()
    )


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get("organization_id") or view.kwargs.get("pk")
        if org_id is None:
            return bool(request.user and request.user.is_authenticated)
        return get_membership(request.user, org_id) is not None


class CanManageOrganization(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get("organization_id") or view.kwargs.get("pk")
        membership = get_membership(request.user, org_id)
        return bool(membership and membership.role in MANAGER_ROLES)
