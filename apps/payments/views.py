from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.audit.services import write_audit_log
from apps.payments.models import (
    PaymentRequest,
    PaymentRequestStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
)
from apps.payments.serializers import (
    CancelPaymentRequestSerializer,
    PaymentManualAmountSerializer,
    PaymentRequestSerializer,
    PaymentTransactionCreateSerializer,
    PaymentTransactionSerializer,
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

        payment_request = serializer.save(
            organization_id=self.get_organization_id_or_raise(),
            created_by=self.request.user,
        )
        write_audit_log(
            action="payment_request.created",
            entity_type="payment_request",
            entity_id=payment_request.id,
            organization_id=payment_request.organization_id,
            actor=self.request.user,
            after_data={
                "reference": payment_request.reference,
                "status": payment_request.status,
                "expected_amount": str(payment_request.expected_amount),
                "paid_amount": str(payment_request.paid_amount),
                "customer_id": payment_request.customer_id,
                "service_id": payment_request.service_id,
            },
            request=self.request,
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
        instance = self.get_object()
        before = {
            "status": instance.status,
            "expected_amount": str(instance.expected_amount),
            "due_date": str(instance.due_date) if instance.due_date else None,
            "notes": instance.notes,
        }
        updated = serializer.save()
        write_audit_log(
            action="payment_request.updated",
            entity_type="payment_request",
            entity_id=updated.id,
            organization_id=updated.organization_id,
            actor=self.request.user,
            before_data=before,
            after_data={
                "status": updated.status,
                "expected_amount": str(updated.expected_amount),
                "due_date": str(updated.due_date) if updated.due_date else None,
                "notes": updated.notes,
            },
            request=self.request,
        )


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

        before = {
            "status": payment_request.status,
            "paid_amount": str(payment_request.paid_amount),
        }
        payment_request.status = PaymentRequestStatus.CANCELLED
        payment_request.save(update_fields=["status", "updated_at"])
        write_audit_log(
            action="payment_request.cancelled",
            entity_type="payment_request",
            entity_id=payment_request.id,
            organization_id=payment_request.organization_id,
            actor=request.user,
            before_data=before,
            after_data={
                "status": payment_request.status,
                "paid_amount": str(payment_request.paid_amount),
            },
            request=request,
        )
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
        before = {
            "status": payment_request.status,
            "paid_amount": str(payment_request.paid_amount),
        }
        try:
            payment_request.apply_manual_payment(amount)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payment_request.save(update_fields=["paid_amount", "status", "updated_at"])
        write_audit_log(
            action="payment_request.manual_payment_applied",
            entity_type="payment_request",
            entity_id=payment_request.id,
            organization_id=payment_request.organization_id,
            actor=request.user,
            before_data=before,
            after_data={
                "status": payment_request.status,
                "paid_amount": str(payment_request.paid_amount),
                "applied_amount": str(amount),
            },
            request=request,
        )
        return Response(PaymentRequestSerializer(payment_request).data)


class PaymentTransactionListCreateView(PaymentRequestBaseMixin, ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentTransactionCreateSerializer
        return PaymentTransactionSerializer

    def get_queryset(self):
        organization_id = self.get_organization_id_or_raise()
        queryset = PaymentTransaction.objects.filter(organization_id=organization_id)

        payment_request_id = self.request.query_params.get("payment_request_id")
        if payment_request_id:
            queryset = queryset.filter(payment_request_id=payment_request_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        reference = self.request.query_params.get("transaction_reference")
        if reference:
            queryset = queryset.filter(transaction_reference__icontains=reference)

        return queryset.select_related("payment_request").order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization_id"] = self.get_organization_id_or_raise()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = self.perform_create(serializer)
        output = PaymentTransactionSerializer(transaction)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        if not has_minimum_role(self.request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour enregistrer une transaction.")

        payment_request = serializer.validated_data["payment_request"]
        transaction_status = serializer.validated_data.get(
            "status", PaymentTransactionStatus.CONFIRMED
        )

        transaction = serializer.save(
            organization_id=self.get_organization_id_or_raise(),
            confirmed_by=self.request.user,
        )
        write_audit_log(
            action="payment_transaction.created",
            entity_type="payment_transaction",
            entity_id=transaction.id,
            organization_id=transaction.organization_id,
            actor=self.request.user,
            after_data={
                "payment_request_id": transaction.payment_request_id,
                "transaction_reference": transaction.transaction_reference,
                "amount_received": str(transaction.amount_received),
                "status": transaction.status,
                "payment_method": transaction.payment_method,
            },
            request=self.request,
        )

        if transaction_status == PaymentTransactionStatus.CONFIRMED:
            before = {
                "status": payment_request.status,
                "paid_amount": str(payment_request.paid_amount),
            }
            try:
                payment_request.apply_manual_payment(transaction.amount_received)
            except ValueError as exc:
                raise ValidationError({"detail": str(exc)})
            payment_request.save(update_fields=["paid_amount", "status", "updated_at"])
            write_audit_log(
                action="payment_request.status_recomputed_from_transaction",
                entity_type="payment_request",
                entity_id=payment_request.id,
                organization_id=payment_request.organization_id,
                actor=self.request.user,
                before_data=before,
                after_data={
                    "status": payment_request.status,
                    "paid_amount": str(payment_request.paid_amount),
                    "trigger_transaction_id": transaction.id,
                },
                request=self.request,
            )
        return transaction


class PaymentRequestTransactionsView(PaymentRequestBaseMixin, ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        payment_request = self.get_scoped_queryset().filter(id=self.kwargs["payment_request_id"]).first()
        if not payment_request:
            return PaymentTransaction.objects.none()
        return (
            PaymentTransaction.objects.filter(payment_request=payment_request)
            .select_related("payment_request")
            .order_by("-created_at")
        )
