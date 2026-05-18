from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.catalog.models import Service
from apps.catalog.serializers import ServiceDeactivateSerializer, ServiceSerializer
from core.api.permissions import has_minimum_role
from core.api.tenancy import resolve_request_organization_id


class ServiceListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer

    def _organization_id_or_raise(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id

    def get_queryset(self):
        organization_id = self._organization_id_or_raise()
        queryset = Service.objects.filter(organization_id=organization_id)

        search = self.request.query_params.get("q", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            normalized = is_active.lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_active=normalized)

        return queryset.order_by("name")

    def perform_create(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour creer un service.")

        serializer.save(
            organization_id=self._organization_id_or_raise(),
            created_by=self.request.user,
        )


class ServiceDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer
    lookup_field = "id"

    def get_queryset(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            return Service.objects.none()
        return Service.objects.filter(organization_id=organization_id)

    def perform_update(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour modifier un service.")
        serializer.save()


class ServiceDeactivateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceDeactivateSerializer

    def post(self, request, service_id):
        if not has_minimum_role(request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour desactiver un service.")

        organization_id = resolve_request_organization_id(request)
        service = Service.objects.filter(id=service_id, organization_id=organization_id).first()
        if not service:
            return Response({"detail": "Service introuvable."}, status=status.HTTP_404_NOT_FOUND)

        service.is_active = False
        service.save(update_fields=["is_active", "updated_at"])
        return Response(ServiceSerializer(service).data)
