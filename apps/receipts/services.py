from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.payments.models import PaymentRequestStatus, PaymentTransaction, PaymentTransactionStatus
from apps.receipts.models import Receipt


def generate_receipt_for_payment_request(*, organization_id, payment_request, transaction=None, issued_by=None):
    if payment_request.organization_id != organization_id:
        raise ValidationError("La demande de paiement ne correspond pas a l'organisation active.")

    if payment_request.status == PaymentRequestStatus.CANCELLED:
        raise ValidationError("Impossible de generer un recu pour une demande annulee.")

    if payment_request.paid_amount <= 0:
        raise ValidationError("Impossible de generer un recu sans montant paye.")

    if transaction is None:
        transaction = (
            PaymentTransaction.objects.filter(
                payment_request=payment_request,
                status=PaymentTransactionStatus.CONFIRMED,
            )
            .order_by("-paid_at", "-id")
            .first()
        )

    if transaction and transaction.payment_request_id != payment_request.id:
        raise ValidationError("La transaction ne correspond pas a la demande de paiement.")

    if transaction and transaction.status != PaymentTransactionStatus.CONFIRMED:
        raise ValidationError("Seules les transactions confirmees peuvent generer un recu.")

    amount_paid = transaction.amount_received if transaction else payment_request.paid_amount

    receipt = Receipt.objects.create(
        organization_id=organization_id,
        payment_request=payment_request,
        transaction=transaction,
        amount_paid=amount_paid,
        currency=payment_request.service.currency,
        payment_status_snapshot=payment_request.status,
        customer_name=payment_request.customer.full_name,
        service_name=payment_request.service.name,
        issued_by=issued_by,
        issued_at=timezone.now(),
    )
    return receipt
