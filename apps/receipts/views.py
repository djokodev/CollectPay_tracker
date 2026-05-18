from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.payments.models import PaymentRequest, PaymentTransaction
from apps.receipts.models import Receipt
from apps.receipts.serializers import (
    GenerateReceiptSerializer,
    ReceiptSerializer,
    ReceiptVerificationSerializer,
)
from apps.receipts.services import generate_receipt_for_payment_request
from core.api.permissions import has_minimum_role
from core.api.tenancy import resolve_request_organization_id


class ReceiptBaseMixin:
    def get_organization_id_or_raise(self):
        organization_id = resolve_request_organization_id(self.request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id


class ReceiptListView(ReceiptBaseMixin, ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReceiptSerializer

    def get_queryset(self):
        organization_id = self.get_organization_id_or_raise()
        queryset = Receipt.objects.filter(organization_id=organization_id)

        payment_request_id = self.request.query_params.get("payment_request_id")
        if payment_request_id:
            queryset = queryset.filter(payment_request_id=payment_request_id)

        return queryset.order_by("-created_at")


class ReceiptDetailView(ReceiptBaseMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReceiptSerializer

    def get(self, request, receipt_id):
        organization_id = self.get_organization_id_or_raise()
        receipt = get_object_or_404(Receipt, id=receipt_id, organization_id=organization_id)
        return Response(self.get_serializer(receipt).data)


class GenerateReceiptView(ReceiptBaseMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GenerateReceiptSerializer

    def post(self, request):
        if not has_minimum_role(request.user, UserRole.AGENT):
            raise PermissionDenied("Role insuffisant pour generer un recu.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id_or_raise()
        payment_request = get_object_or_404(
            PaymentRequest,
            id=serializer.validated_data["payment_request_id"],
            organization_id=organization_id,
        )

        transaction_id = serializer.validated_data.get("transaction_id")
        transaction = None
        if transaction_id is not None:
            transaction = get_object_or_404(
                PaymentTransaction,
                id=transaction_id,
                organization_id=organization_id,
            )
            if transaction.payment_request_id != payment_request.id:
                raise ValidationError(
                    {"transaction_id": "La transaction ne correspond pas a la demande fournie."}
                )

        receipt = generate_receipt_for_payment_request(
            organization_id=organization_id,
            payment_request=payment_request,
            transaction=transaction,
            issued_by=request.user,
        )
        return Response(ReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


class VerifyReceiptPublicView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ReceiptVerificationSerializer

    def get(self, request, public_reference):
        receipt = get_object_or_404(Receipt, public_reference=public_reference)
        payload = {
            "receipt_number": receipt.receipt_number,
            "public_reference": receipt.public_reference,
            "is_valid": receipt.is_verification_valid(),
            "amount_paid": receipt.amount_paid,
            "currency": receipt.currency,
            "customer_name": receipt.customer_name,
            "service_name": receipt.service_name,
            "issued_at": receipt.issued_at,
        }
        return Response(payload)
