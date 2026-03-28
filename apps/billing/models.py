from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.core.models import CompanyScopedModel, SystemSetting
from apps.customers.models import Customer
from apps.services_app.models import CustomerService


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120)
    symbol = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.code


class Invoice(CompanyScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        ISSUED = "issued", "Emitida"
        PAID = "paid", "Pagada"
        OVERDUE = "overdue", "Vencida"
        CANCELLED = "cancelled", "Anulada"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        unique_together = [("company", "invoice_number")]

    def __str__(self):
        return self.invoice_number

    def calculate_totals(self):
        self.total_amount = (self.subtotal + self.tax_amount + self.late_fee) - self.discount_amount
        self.balance_due = self.total_amount - self.amount_paid
        if self.balance_due <= Decimal("0.00") and self.status != self.Status.CANCELLED:
            self.status = self.Status.PAID
            self.balance_due = Decimal("0.00")
        elif self.status != self.Status.CANCELLED and self.due_date < timezone.localdate() and self.balance_due > Decimal("0.00"):
            self.status = self.Status.OVERDUE
        elif self.status != self.Status.CANCELLED and self.total_amount > Decimal("0.00"):
            self.status = self.Status.ISSUED

    @classmethod
    def next_invoice_number(cls, company):
        setting = SystemSetting.objects.get(company=company)
        number = f"{setting.invoice_prefix}-{setting.invoice_sequence:06d}"
        setting.invoice_sequence += 1
        setting.save(update_fields=["invoice_sequence", "updated_at"])
        return number

    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)


class InvoiceItem(CompanyScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(CustomerService, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(CompanyScopedModel):
    class Method(models.TextChoices):
        CASH_USD = "cash_usd", "Efectivo USD"
        CASH_EUR = "cash_eur", "Efectivo EUR"
        CUP = "cup", "CUP"
        PAYPAL = "paypal", "PayPal"
        SEPA_EUR = "sepa_eur", "Transferencia SEPA Europa"
        TRANSFER = "transfer", "Transferencia bancaria"
        CRYPTO = "crypto", "Criptomonedas"
        OTHER = "other", "Otros"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH_USD)
    reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)
    registered_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="registered_payments")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-paid_at"]

    @transaction.atomic
    def apply(self):
        if self.invoice:
            self.invoice.amount_paid += self.amount
            self.invoice.save()


class SuspensionEvent(CompanyScopedModel):
    class Action(models.TextChoices):
        SUSPEND = "suspend", "Suspender"
        REACTIVATE = "reactivate", "Reactivar"
        WARNING = "warning", "Aviso"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="suspension_events")
    service = models.ForeignKey(CustomerService, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.CharField(max_length=255)
    technical_executed = models.BooleanField(default=False)
    integration_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
