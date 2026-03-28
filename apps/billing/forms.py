from django import forms
from django.forms import inlineformset_factory

from apps.billing.models import Invoice, InvoiceItem, Payment, SuspensionEvent


class InvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    class Meta:
        model = Invoice
        fields = [
            "customer", "issue_date", "due_date", "subtotal", "tax_amount",
            "discount_amount", "late_fee", "currency", "notes", "is_recurring",
        ]


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    fields=["service", "description", "quantity", "unit_price"],
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        self.fields["method"].help_text = "Selecciona el canal exacto: efectivo USD/EUR, PayPal, criptomonedas, SEPA o transferencia."

    class Meta:
        model = Payment
        fields = ["customer", "invoice", "amount", "currency", "method", "reference", "paid_at", "notes"]
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class SuspensionEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    class Meta:
        model = SuspensionEvent
        fields = ["customer", "service", "action", "reason", "notes"]
