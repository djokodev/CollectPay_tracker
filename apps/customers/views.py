from django.apps import apps
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerDeactivateSerializer,
    CustomerHistorySerializer,
    CustomerSerializer,
)
from core.api.permissions import has_minimum_role
from core.api.tenancy import resolve_request_organization_id


class CustomerListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer

    def _get_organization_id_or_raise(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id

    def get_queryset(self):
        organization_id = self._get_organization_id_or_raise()
        queryset = Customer.objects.filter(organization_id=organization_id)

        search = self.request.query_params.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            normalized = is_active.lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_active=normalized)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour creer un client.")

        organization_id = self._get_organization_id_or_raise()
        serializer.save(
            organization_id=organization_id,
            created_by=self.request.user,
        )


class CustomerDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    lookup_field = "id"

    def get_queryset(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            return Customer.objects.none()
        return Customer.objects.filter(organization_id=organization_id)

    def perform_update(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour modifier un client.")
        serializer.save()


class CustomerDeactivateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerDeactivateSerializer

    def post(self, request, customer_id):
        if not has_minimum_role(request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour desactiver un client.")

        organization_id = resolve_request_organization_id(request)
        customer = Customer.objects.filter(
            id=customer_id,
            organization_id=organization_id,
        ).first()
        if not customer:
            return Response({"detail": "Client introuvable."}, status=status.HTTP_404_NOT_FOUND)

        customer.is_active = False
        customer.save(update_fields=["is_active", "updated_at"])
        return Response(CustomerSerializer(customer).data)


class CustomerPaymentHistoryView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerHistorySerializer

    def get(self, request, customer_id):
        organization_id = resolve_request_organization_id(request)
        customer = Customer.objects.filter(
            id=customer_id,
            organization_id=organization_id,
        ).first()
        if not customer:
            return Response({"detail": "Client introuvable."}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            "customer": CustomerSerializer(customer).data,
            "payment_requests": [],
            "transactions": [],
        }

        try:
            payment_request_model = apps.get_model("payments", "PaymentRequest")
        except LookupError:
            payment_request_model = None
        try:
            transaction_model = apps.get_model("payments", "PaymentTransaction")
        except LookupError:
            transaction_model = None

        if payment_request_model and hasattr(payment_request_model, "customer_id"):
            payment_requests = payment_request_model.objects.filter(customer_id=customer.id).values(
                "id",
                "status",
                "created_at",
            )
            payload["payment_requests"] = list(payment_requests)

        if transaction_model and hasattr(transaction_model, "payment_request_id") and payment_request_model:
            payment_request_ids = payment_request_model.objects.filter(customer_id=customer.id).values_list(
                "id", flat=True
            )
            transactions = transaction_model.objects.filter(
                payment_request_id__in=payment_request_ids
            ).values("id", "status", "amount_received", "transaction_reference", "created_at")
            payload["transactions"] = list(transactions)

        return Response(payload)
