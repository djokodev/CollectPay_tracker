import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PaymentRequestStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    PARTIAL = "PARTIAL", "Partiel"
    PAID = "PAID", "Paye"
    FAILED = "FAILED", "Echoue"
    CANCELLED = "CANCELLED", "Annule"
    REFUNDED = "REFUNDED", "Rembourse"


class PaymentRequest(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="payment_requests",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="payment_requests",
    )
    service = models.ForeignKey(
        "catalog.Service",
        on_delete=models.PROTECT,
        related_name="payment_requests",
    )
    reference = models.CharField(max_length=40)
    expected_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentRequestStatus.choices,
        default=PaymentRequestStatus.PENDING,
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_payment_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "reference"],
                name="uniq_payment_request_reference_per_org",
            )
        ]

    @property
    def remaining_amount(self):
        remaining = self.expected_amount - self.paid_amount
        return remaining if remaining > 0 else Decimal("0.00")

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PRQ-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def recompute_status(self):
        if self.status == PaymentRequestStatus.CANCELLED:
            return

        if self.paid_amount <= Decimal("0.00"):
            self.status = PaymentRequestStatus.PENDING
        elif self.paid_amount < self.expected_amount:
            self.status = PaymentRequestStatus.PARTIAL
        else:
            self.status = PaymentRequestStatus.PAID

    def apply_manual_payment(self, amount):
        if self.status == PaymentRequestStatus.CANCELLED:
            raise ValueError("Une demande annulee ne peut pas recevoir de paiement.")

        self.paid_amount += amount
        self.recompute_status()

    def __str__(self):
        return f"{self.reference} - {self.customer}"
