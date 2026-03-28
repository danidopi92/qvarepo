from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteModel(TimeStampedModel):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_%(class)ss",
    )

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])


class Company(TimeStampedModel):
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    logo = models.FileField(upload_to="company_logos/", blank=True, null=True)
    default_currency = models.CharField(max_length=10, default=settings.SYSTEM_DEFAULT_CURRENCY)
    timezone = models.CharField(max_length=64, default="America/Havana")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class CompanyScopedModel(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_%(class)ss",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_%(class)ss",
    )

    class Meta:
        abstract = True


class SystemSetting(TimeStampedModel):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)
    invoice_prefix = models.CharField(max_length=20, default="QVT")
    invoice_sequence = models.PositiveIntegerField(default=1)
    default_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    payment_grace_days = models.PositiveIntegerField(default=5)
    reminder_days_before_due = models.PositiveIntegerField(default=2)
    suspension_days_after_due = models.PositiveIntegerField(default=10)
    enable_multi_currency = models.BooleanField(default=True)

    @classmethod
    def load(cls):
        company = Company.objects.filter(is_active=True).order_by("id").first()
        if not company:
            return None
        setting, _ = cls.objects.get_or_create(company=company)
        return setting


class AuditLog(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    model_name = models.CharField(max_length=120)
    object_id = models.CharField(max_length=64)
    action = models.CharField(max_length=50)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_name}:{self.object_id}:{self.action}"
