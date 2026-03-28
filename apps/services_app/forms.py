from django import forms

from apps.core.forms import StyledModelForm
from apps.services_app.models import CustomerService, ServicePlan


class CustomerServiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    class Meta:
        model = CustomerService
        fields = [
            "customer", "plan", "service_type", "speed_label", "monthly_price", "start_date",
            "cut_off_date", "status", "equipment", "router_cpe", "mac_address",
            "technical_reference", "pppoe_username", "node",
        ]


class ServicePlanForm(StyledModelForm):
    class Meta:
        model = ServicePlan
        fields = ["name", "service_type", "speed_label", "monthly_price", "description", "is_recurring"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}
