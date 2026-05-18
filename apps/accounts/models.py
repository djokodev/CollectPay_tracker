from django.conf import settings
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Administrateur"
    MANAGER = "MANAGER", "Manager"
    AGENT = "AGENT", "Agent"
    VIEWER = "VIEWER", "Lecture"


class AccountProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.AGENT)
    phone = models.CharField(max_length=20, blank=True)
    active_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_profiles",
    )
    is_active_member = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil de compte"
        verbose_name_plural = "Profils de comptes"

    def __str__(self):
        return f"{self.user.username} ({self.role})"
