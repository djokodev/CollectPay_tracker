from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class CurrencyCode(models.TextChoices):
    XAF = "XAF", "Franc CFA"
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"


class Service(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    expected_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=10, choices=CurrencyCode.choices, default=CurrencyCode.XAF)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_services",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_service_name_per_organization",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"
