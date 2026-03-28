from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.customers.models import Customer


class CustomerPortalAccount(TimeStampedModel):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="portal_account")
    email_login = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invited_portal_accounts",
    )

    class Meta:
        ordering = ["customer__full_name"]

    def __str__(self):
        return f"{self.customer.full_name} <{self.email_login}>"

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def mark_logged_in(self):
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])
