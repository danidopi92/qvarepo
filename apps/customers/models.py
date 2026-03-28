from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from apps.core.models import CompanyScopedModel


class Node(CompanyScopedModel):
    name = models.CharField(max_length=120, db_index=True)
    zone = models.CharField(max_length=120, blank=True, db_index=True)
    code = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("company", "name")]

    def __str__(self):
        return self.name


class Customer(CompanyScopedModel):
    class CustomerType(models.TextChoices):
        RESIDENTIAL = "residential", "Residencial"
        BUSINESS = "business", "Empresarial"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        SUSPENDED = "suspended", "Suspendido"
        INACTIVE = "inactive", "Inactivo"
        LEAD = "lead", "Prospecto"

    class PreferredPaymentMethod(models.TextChoices):
        CASH_USD = "cash_usd", "Efectivo USD"
        CASH_EUR = "cash_eur", "Efectivo EUR"
        CUP = "cup", "CUP"
        PAYPAL = "paypal", "PayPal"
        SEPA_EUR = "sepa_eur", "Transferencia SEPA Europa"
        TRANSFER = "transfer", "Transferencia bancaria"
        CRYPTO = "crypto", "Criptomonedas"
        OTHER = "other", "Otros"

    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.RESIDENTIAL)
    full_name = models.CharField(max_length=255, db_index=True)
    document_id = models.CharField(max_length=64, blank=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True, db_index=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    address = models.TextField(blank=True)
    location_reference = models.CharField(max_length=255, blank=True)
    coordinates = models.CharField(max_length=120, blank=True)
    node = models.ForeignKey(Node, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_ip = models.GenericIPAddressField(null=True, blank=True, protocol="IPv4", db_index=True)
    payment_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    preferred_payment_method = models.CharField(
        max_length=20,
        choices=PreferredPaymentMethod.choices,
        blank=True,
        db_index=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    internal_notes = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["company", "full_name"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "assigned_ip"]),
        ]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("customer-detail", args=[self.pk])

    @property
    def can_be_permanently_deleted(self):
        return not self.invoices.exists() and not self.payments.exists()


class CustomerContact(CompanyScopedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "name"]


class CustomerNote(CompanyScopedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notes")
    note = models.TextField()
    is_important = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class CustomerDocument(CompanyScopedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="customer_documents/")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
