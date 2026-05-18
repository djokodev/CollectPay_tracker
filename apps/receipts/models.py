import hashlib
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Receipt(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    payment_request = models.ForeignKey(
        "payments.PaymentRequest",
        on_delete=models.PROTECT,
        related_name="receipts",
    )
    transaction = models.ForeignKey(
        "payments.PaymentTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="receipts",
    )
    receipt_number = models.CharField(max_length=40)
    public_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    verification_hash = models.CharField(max_length=64)

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=10, default="XAF")
    payment_status_snapshot = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=220)
    service_name = models.CharField(max_length=220)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_receipts",
    )
    issued_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "receipt_number"],
                name="uniq_receipt_number_per_org",
            )
        ]

    def build_verification_hash(self):
        salt = settings.RECEIPT_VERIFICATION_SALT
        payload = (
            f"{self.organization_id}|{self.receipt_number}|{self.public_reference}|"
            f"{self.payment_request.reference}|{self.amount_paid}|{self.issued_at.isoformat()}|{salt}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP-{uuid.uuid4().hex[:12].upper()}"
        if not self.verification_hash:
            self.verification_hash = self.build_verification_hash()
        super().save(*args, **kwargs)

    def is_verification_valid(self):
        return self.verification_hash == self.build_verification_hash()

    def __str__(self):
        return f"{self.receipt_number} - {self.payment_request.reference}"
