from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole
from apps.organizations.permissions import CanManageOrganization, MANAGER_ROLES, get_membership
from apps.organizations.serializers import (
    AddOrganizationMemberSerializer,
    OrganizationMembershipSerializer,
    OrganizationSerializer,
    SwitchActiveOrganizationSerializer,
)
from core.api.permissions import has_minimum_role


class OrganizationListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.MANAGER):
            raise PermissionDenied("Seuls les managers et admins peuvent creer une organisation.")

        organization = serializer.save()
        OrganizationMembership.objects.create(
            organization=organization,
            user=self.request.user,
            role=OrganizationRole.OWNER,
        )

        profile = self.request.user.account_profile
        if profile.active_organization_id is None:
            profile.active_organization = organization
            profile.save(update_fields=["active_organization", "updated_at"])


class OrganizationDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    def perform_update(self, serializer):
        membership = get_membership(self.request.user, serializer.instance.id)
        if not membership or membership.role not in MANAGER_ROLES:
            raise PermissionDenied("Seuls les managers de l'organisation peuvent la modifier.")
        serializer.save()


class OrganizationMemberListCreateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddOrganizationMemberSerializer

    def get(self, request, organization_id):
        membership = get_membership(request.user, organization_id)
        if not membership:
            raise PermissionDenied("Acces refuse a cette organisation.")

        queryset = OrganizationMembership.objects.filter(
            organization_id=organization_id,
            is_active=True,
        ).select_related("user", "organization")
        data = OrganizationMembershipSerializer(queryset, many=True).data
        return Response(data)

    def post(self, request, organization_id):
        current_membership = get_membership(request.user, organization_id)
        if not current_membership or current_membership.role not in MANAGER_ROLES:
            raise PermissionDenied("Permission insuffisante pour gerer les membres.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_role = serializer.validated_data["role"]
        if target_role in {OrganizationRole.OWNER, OrganizationRole.ADMIN} and current_membership.role not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        }:
            raise PermissionDenied("Seuls owner/admin peuvent assigner les roles owner/admin.")

        obj, created = OrganizationMembership.objects.update_or_create(
            organization_id=organization_id,
            user_id=serializer.validated_data["user_id"],
            defaults={"role": target_role, "is_active": True},
        )

        data = OrganizationMembershipSerializer(obj).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class OrganizationMemberRoleUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticated, CanManageOrganization]
    serializer_class = AddOrganizationMemberSerializer

    def patch(self, request, organization_id, membership_id):
        membership = get_object_or_404(
            OrganizationMembership,
            id=membership_id,
            organization_id=organization_id,
        )
        actor = get_membership(request.user, organization_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if membership.role == OrganizationRole.OWNER and actor.role != OrganizationRole.OWNER:
            raise PermissionDenied("Seul le owner peut modifier le role d'un owner.")

        if new_role in {OrganizationRole.OWNER, OrganizationRole.ADMIN} and actor.role not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        }:
            raise PermissionDenied("Seuls owner/admin peuvent attribuer owner/admin.")

        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])
        return Response(OrganizationMembershipSerializer(membership).data)


class MyOrganizationsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get(self, request):
        organizations = Organization.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
        ).distinct()
        data = OrganizationSerializer(organizations, many=True).data
        return Response(data)


class SwitchActiveOrganizationView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SwitchActiveOrganizationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data["organization_id"]

        membership = get_membership(request.user, organization_id)
        if not membership:
            raise PermissionDenied("Impossible de selectionner une organisation non associee.")

        profile = request.user.account_profile
        profile.active_organization_id = organization_id
        profile.save(update_fields=["active_organization", "updated_at"])

        return Response(
            {
                "active_organization_id": organization_id,
                "organization": membership.organization.name,
            },
            status=status.HTTP_200_OK,
        )
