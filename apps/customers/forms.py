from django import forms

from apps.customers.models import Customer, CustomerContact, CustomerNote, Node
from apps.services_app.models import ServicePlan


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-control"
            if isinstance(field.widget, (forms.Select,)):
                css_class = "form-select"
            if isinstance(field.widget, (forms.CheckboxInput,)):
                css_class = "form-check-input"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css_class}".strip()


class CustomerForm(BootstrapModelForm):
    service_plan = forms.ModelChoiceField(
        queryset=ServicePlan.objects.none(),
        required=False,
        label="Plan principal",
    )

    class Meta:
        model = Customer
        fields = [
            "customer_type", "full_name", "document_id", "phone", "whatsapp", "email",
            "address", "location_reference", "node", "assigned_ip",
            "payment_day", "preferred_payment_method", "status", "internal_notes", "tags",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "customer_type": "Tipo de cliente",
            "full_name": "Nombre",
            "document_id": "Documento",
            "phone": "Teléfono",
            "whatsapp": "WhatsApp",
            "email": "Correo",
            "address": "Dirección",
            "location_reference": "Referencia de ubicación",
            "node": "Nodo",
            "assigned_ip": "IP",
            "payment_day": "Día de pago",
            "service_plan": "Plan principal",
            "preferred_payment_method": "Tipo de pago",
            "status": "Estado",
            "internal_notes": "Notas",
            "tags": "Etiquetas",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = None
        if self.instance and self.instance.pk:
            company = self.instance.company
        if company:
            self.fields["service_plan"].queryset = ServicePlan.objects.filter(company=company, is_deleted=False).order_by("name")
            primary_service = self.instance.services.filter(is_deleted=False).select_related("plan").order_by("created_at").first()
            if primary_service:
                self.fields["service_plan"].initial = primary_service.plan
        else:
            self.fields["service_plan"].queryset = ServicePlan.objects.filter(is_deleted=False).order_by("name")
        self.fields["full_name"].widget.attrs["placeholder"] = "Nombre completo o razón social"
        self.fields["document_id"].widget.attrs["placeholder"] = "CI, DNI, pasaporte o NIF"
        self.fields["phone"].widget.attrs["placeholder"] = "Teléfono principal"
        self.fields["whatsapp"].widget.attrs["placeholder"] = "Número de WhatsApp"
        self.fields["email"].widget.attrs["placeholder"] = "correo@cliente.com"
        self.fields["address"].widget.attrs["placeholder"] = "Dirección del cliente"
        self.fields["location_reference"].widget.attrs["placeholder"] = "Referencia para ubicar el servicio"
        self.fields["assigned_ip"].widget.attrs["placeholder"] = "Ej: 192.168.10.25"
        self.fields["payment_day"].widget.attrs["placeholder"] = "1 a 31"
        self.fields["internal_notes"].widget.attrs["placeholder"] = "Observaciones internas de cobro o soporte"
        self.fields["tags"].widget.attrs["placeholder"] = "vip, empresa, moroso"


class CustomerContactForm(BootstrapModelForm):
    class Meta:
        model = CustomerContact
        fields = ["name", "role", "phone", "email", "is_primary"]


class CustomerNoteForm(BootstrapModelForm):
    class Meta:
        model = CustomerNote
        fields = ["note", "is_important"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}


class ImportCustomersForm(forms.Form):
    file = forms.FileField()


class NodeForm(BootstrapModelForm):
    class Meta:
        model = Node
        fields = ["name", "zone", "code", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "name": "Nombre del nodo",
            "zone": "Zona",
            "code": "Código",
            "description": "Descripción",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["placeholder"] = "Ej: Nodo Central"
        self.fields["zone"].widget.attrs["placeholder"] = "Ej: Centro"
        self.fields["code"].widget.attrs["placeholder"] = "Ej: NODO-CEN-01"
        self.fields["description"].widget.attrs["placeholder"] = "Notas operativas del nodo"
