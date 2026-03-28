from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from apps.core.models import Company, SystemSetting


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"


class CompanyBrandingForm(StyledModelForm):
    class Meta:
        model = Company
        fields = ["name", "legal_name", "tax_id", "email", "phone", "address", "default_currency", "timezone", "logo"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class SystemSettingForm(StyledModelForm):
    class Meta:
        model = SystemSetting
        fields = [
            "invoice_prefix",
            "invoice_sequence",
            "default_tax_percent",
            "payment_grace_days",
            "reminder_days_before_due",
            "suspension_days_after_due",
            "enable_multi_currency",
        ]


class UserRoleForm(UserCreationForm):
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False, widget=forms.SelectMultiple)
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "is_active", "groups")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class UserUpdateForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False, widget=forms.SelectMultiple)

    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email", "is_active", "groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].initial = self.instance.groups.all()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class AdminBootstrapForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if commit:
            user.save()
        return user


class ResetPlatformForm(forms.Form):
    confirmation = forms.CharField(
        label="Escribe RESET TOTAL para confirmar",
        help_text="Esta acción elimina clientes, nodos, planes, servicios, facturas, pagos, eventos y cuentas del portal.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["confirmation"].widget.attrs["class"] = "form-control"
        self.fields["confirmation"].widget.attrs["placeholder"] = "RESET TOTAL"

    def clean_confirmation(self):
        value = self.cleaned_data["confirmation"].strip().upper()
        if value != "RESET TOTAL":
            raise forms.ValidationError("Debes escribir exactamente RESET TOTAL.")
        return value
