from django import forms

from apps.client_portal.models import CustomerPortalAccount


class ClientPortalAccessForm(forms.Form):
    identifier = forms.CharField(
        label="Código o documento del cliente",
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": "Ej: 15 o DNI/NIF"}),
    )
    phone = forms.CharField(
        label="Teléfono o WhatsApp asociado",
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "Ingresa tu teléfono registrado"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class ClientPortalLoginForm(forms.Form):
    email_login = forms.EmailField(
        label="Correo de acceso",
        widget=forms.EmailInput(attrs={"placeholder": "cliente@correo.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Tu contraseña"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        email_login = cleaned_data.get("email_login")
        password = cleaned_data.get("password")
        if not email_login or not password:
            return cleaned_data
        account = CustomerPortalAccount.objects.select_related("customer").filter(email_login__iexact=email_login).first()
        if not account or not account.check_password(password):
            raise forms.ValidationError("Correo o contraseña incorrectos.")
        if not account.is_active:
            raise forms.ValidationError("Tu cuenta del portal está desactivada. Contacta con QvaTel.")
        cleaned_data["account"] = account
        return cleaned_data


class ClientPortalRegistrationForm(forms.Form):
    identifier = forms.CharField(
        label="Código o documento del cliente",
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": "Ej: 15 o DNI/NIF"}),
    )
    phone = forms.CharField(
        label="Teléfono o WhatsApp asociado",
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "Ingresa tu teléfono registrado"}),
    )
    email_login = forms.EmailField(
        label="Correo para iniciar sesión",
        widget=forms.EmailInput(attrs={"placeholder": "cliente@correo.com"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 8 caracteres"}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Repite tu contraseña"}),
        min_length=8,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data


class ClientPortalInviteRegistrationForm(forms.Form):
    email_login = forms.EmailField(
        label="Correo para iniciar sesión",
        widget=forms.EmailInput(attrs={"placeholder": "cliente@correo.com"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 8 caracteres"}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Repite tu contraseña"}),
        min_length=8,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data


class ClientPortalRecoveryForm(forms.Form):
    identifier = forms.CharField(
        label="Código o documento del cliente",
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": "Ej: 15 o DNI/NIF"}),
    )
    phone = forms.CharField(
        label="Teléfono o WhatsApp asociado",
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "Ingresa tu teléfono registrado"}),
    )
    email_login = forms.EmailField(
        label="Correo de tu cuenta portal",
        widget=forms.EmailInput(attrs={"placeholder": "cliente@correo.com"}),
    )
    password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 8 caracteres"}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Repite tu contraseña"}),
        min_length=8,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
