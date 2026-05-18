from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import UserRole


ROLE_LEVEL = {
    UserRole.VIEWER: 1,
    UserRole.AGENT: 2,
    UserRole.MANAGER: 3,
    UserRole.ADMIN: 4,
}


def get_user_role(user):
    if not user or not user.is_authenticated:
        return None

    profile = getattr(user, "account_profile", None)
    if not profile:
        return None
    return profile.role


def has_minimum_role(user, minimum_role):
    current_role = get_user_role(user)
    if current_role is None:
        return False
    return ROLE_LEVEL.get(current_role, 0) >= ROLE_LEVEL.get(minimum_role, 0)


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrReadOnly(BasePermission):
    owner_field = "created_by"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        owner = getattr(obj, self.owner_field, None)
        return bool(request.user and request.user.is_authenticated and owner == request.user)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return has_minimum_role(request.user, UserRole.ADMIN)


class IsAdminOrManagerRole(BasePermission):
    def has_permission(self, request, view):
        return has_minimum_role(request.user, UserRole.MANAGER)


class IsAgentOrAboveRole(BasePermission):
    def has_permission(self, request, view):
        return has_minimum_role(request.user, UserRole.AGENT)
