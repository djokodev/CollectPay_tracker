from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from core.api.tenancy import resolve_request_organization_id


class AuditLogListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        organization_id = resolve_request_organization_id(self.request)
        queryset = AuditLog.objects.all()

        if organization_id is not None:
            queryset = queryset.filter(organization_id=organization_id)

        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        entity_id = self.request.query_params.get("entity_id")
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        actor_id = self.request.query_params.get("actor_id")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

        return queryset.order_by("-created_at")
