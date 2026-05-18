from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.payments.models import PaymentRequest, PaymentRequestStatus
from apps.payments.serializers import (
    CancelPaymentRequestSerializer,
    PaymentManualAmountSerializer,
    PaymentRequestSerializer,
)
from core.api.permissions import has_minimum_role
from core.api.tenancy import resolve_request_organization_id


class PaymentRequestBaseMixin:
    def get_organization_id_or_raise(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id

    def get_scoped_queryset(self):
        organization_id = self.get_organization_id_or_raise()
        return PaymentRequest.objects.filter(organization_id=organization_id)


class PaymentRequestListCreateView(PaymentRequestBaseMixin, ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer

    def get_queryset(self):
        queryset = self.get_scoped_queryset()

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        customer_id = self.request.query_params.get("customer_id")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        service_id = self.request.query_params.get("service_id")
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        overdue = self.request.query_params.get("overdue")
        if overdue and overdue.lower() in {"1", "true", "yes"}:
            today = timezone.localdate()
            queryset = queryset.filter(
                due_date__lt=today,
                status__in=[PaymentRequestStatus.PENDING, PaymentRequestStatus.PARTIAL],
            )

        return queryset.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization_id"] = self.get_organization_id_or_raise()
        return context

    def perform_create(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour creer une demande de paiement.")

        serializer.save(
            organization_id=self.get_organization_id_or_raise(),
            created_by=self.request.user,
        )


class PaymentRequestDetailView(PaymentRequestBaseMixin, RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer
    lookup_field = "id"

    def get_queryset(self):
        return self.get_scoped_queryset()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization_id"] = self.get_organization_id_or_raise()
        return context

    def perform_update(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour modifier une demande de paiement.")
        serializer.save()


class PaymentRequestsByStatusView(PaymentRequestBaseMixin, ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer
    target_status = None
    overdue_only = False

    def get_queryset(self):
        queryset = self.get_scoped_queryset()
        if self.target_status:
            queryset = queryset.filter(status=self.target_status)
        if self.overdue_only:
            today = timezone.localdate()
            queryset = queryset.filter(
                due_date__lt=today,
                status__in=[PaymentRequestStatus.PENDING, PaymentRequestStatus.PARTIAL],
            )
        return queryset.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization_id"] = self.get_organization_id_or_raise()
        return context


class PendingPaymentRequestsView(PaymentRequestsByStatusView):
    target_status = PaymentRequestStatus.PENDING


class PartialPaymentRequestsView(PaymentRequestsByStatusView):
    target_status = PaymentRequestStatus.PARTIAL


class OverduePaymentRequestsView(PaymentRequestsByStatusView):
    overdue_only = True


class CancelPaymentRequestView(PaymentRequestBaseMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CancelPaymentRequestSerializer

    def post(self, request, payment_request_id):
        if not has_minimum_role(request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour annuler une demande de paiement.")

        payment_request = self.get_scoped_queryset().filter(id=payment_request_id).first()
        if not payment_request:
            return Response({"detail": "Demande introuvable."}, status=status.HTTP_404_NOT_FOUND)

        payment_request.status = PaymentRequestStatus.CANCELLED
        payment_request.save(update_fields=["status", "updated_at"])
        return Response(PaymentRequestSerializer(payment_request).data)


class ApplyManualPaymentView(PaymentRequestBaseMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentManualAmountSerializer

    def post(self, request, payment_request_id):
        if not has_minimum_role(request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour enregistrer un paiement manuel.")

        payment_request = self.get_scoped_queryset().filter(id=payment_request_id).first()
        if not payment_request:
            return Response({"detail": "Demande introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]
        try:
            payment_request.apply_manual_payment(amount)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payment_request.save(update_fields=["paid_amount", "status", "updated_at"])
        return Response(PaymentRequestSerializer(payment_request).data)
