from django.urls import path

from apps.organizations.views import (
    MyOrganizationsView,
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationMemberListCreateView,
    OrganizationMemberRoleUpdateView,
    SwitchActiveOrganizationView,
)

urlpatterns = [
    path("", OrganizationListCreateView.as_view(), name="organizations-list-create"),
    path("mine/", MyOrganizationsView.as_view(), name="organizations-mine"),
    path("switch-active/", SwitchActiveOrganizationView.as_view(), name="organizations-switch-active"),
    path("<int:pk>/", OrganizationDetailView.as_view(), name="organizations-detail"),
    path(
        "<int:organization_id>/members/",
        OrganizationMemberListCreateView.as_view(),
        name="organizations-members",
    ),
    path(
        "<int:organization_id>/members/<int:membership_id>/role/",
        OrganizationMemberRoleUpdateView.as_view(),
        name="organizations-member-role-update",
    ),
]
