import re

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.billing.models import Invoice, Payment
from apps.client_portal.forms import (
    ClientPortalAccessForm,
    ClientPortalInviteRegistrationForm,
    ClientPortalLoginForm,
    ClientPortalRecoveryForm,
    ClientPortalRegistrationForm,
)
from apps.client_portal.models import CustomerPortalAccount
from apps.client_portal.services import (
    build_portal_access_token,
    resolve_portal_access_token,
    resolve_portal_register_token,
)
from apps.core.models import Company
from apps.core.security import clear_rate_limit, is_rate_limited, record_rate_limit_failure
from apps.customers.models import Customer
from apps.services_app.models import CustomerService

PORTAL_SESSION_KEY = "client_portal_customer_id"
PORTAL_ACCOUNT_SESSION_KEY = "client_portal_account_id"


def normalize_digits(value):
    return re.sub(r"\D", "", value or "")


def authenticate_customer_identity(company, identifier, phone):
    identifier = (identifier or "").strip()
    phone_digits = normalize_digits(phone)
    candidates = Customer.objects.filter(company=company, is_deleted=False)
    if identifier.isdigit():
        candidates = candidates.filter(pk=int(identifier))
    else:
        candidates = candidates.filter(document_id__iexact=identifier)
    for customer in candidates:
        customer_phones = [normalize_digits(customer.phone), normalize_digits(customer.whatsapp)]
        if phone_digits and any(stored and stored.endswith(phone_digits) for stored in customer_phones):
            return customer
    return None


def ensure_not_rate_limited(request, scope, identity=""):
    if is_rate_limited(scope, request, identity):
        messages.error(request, "Demasiados intentos. Espera unos minutos antes de volver a probar.")
        return False
    return True


class ClientPortalSessionMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).order_by("id").first()

    def get_portal_account(self):
        account_id = self.request.session.get(PORTAL_ACCOUNT_SESSION_KEY)
        if not account_id:
            return None
        return CustomerPortalAccount.objects.select_related("customer", "customer__company").filter(pk=account_id).first()

    def get_customer(self):
        account = self.get_portal_account()
        if account and account.customer and not account.customer.is_deleted:
            return account.customer
        customer_id = self.request.session.get(PORTAL_SESSION_KEY)
        if not customer_id:
            return None
        company = self.get_company()
        return Customer.objects.filter(company=company, pk=customer_id, is_deleted=False).first()

    def dispatch(self, request, *args, **kwargs):
        if not self.get_customer():
            return redirect("portal-access")
        return super().dispatch(request, *args, **kwargs)

    def build_customer_context(self):
        customer = self.get_customer()
        account = self.get_portal_account()
        active_services = CustomerService.objects.filter(
            company=customer.company,
            customer=customer,
            is_deleted=False,
        ).select_related("plan", "node", "equipment")
        invoices = Invoice.objects.filter(company=customer.company, customer=customer, is_deleted=False)
        pending_invoices = invoices.exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]).order_by("due_date")
        payments = Payment.objects.filter(company=customer.company, customer=customer, is_deleted=False).order_by("-paid_at")
        return {
            "portal_customer": customer,
            "portal_account": account,
            "portal_services": active_services,
            "portal_primary_service": active_services.filter(status=CustomerService.Status.ACTIVE).first() or active_services.first(),
            "portal_pending_invoices": pending_invoices[:5],
            "portal_recent_payments": payments[:5],
            "portal_balance_total": pending_invoices.aggregate(total=Sum("balance_due"))["total"] or 0,
            "portal_next_due_invoice": pending_invoices.first(),
        }


class ClientPortalHomeRedirectView(View):
    def get(self, request):
        if request.session.get(PORTAL_SESSION_KEY):
            return redirect("portal-dashboard")
        return redirect("portal-access")


class ClientPortalAccessView(View):
    template_name = "portal/access.html"

    def get_company(self):
        return Company.objects.filter(is_active=True).order_by("id").first()

    def get(self, request):
        if request.session.get(PORTAL_SESSION_KEY) or request.session.get(PORTAL_ACCOUNT_SESSION_KEY):
            return redirect("portal-dashboard")
        token = request.GET.get("token")
        if token:
            customer = self.authenticate_by_token(self.get_company(), token)
            if customer:
                request.session[PORTAL_SESSION_KEY] = customer.pk
                request.session.pop(PORTAL_ACCOUNT_SESSION_KEY, None)
                request.session.set_expiry(60 * 60 * 8)
                messages.success(request, f"Acceso seguro concedido para {customer.full_name}.")
                return redirect("portal-dashboard")
            messages.error(request, "El enlace seguro del portal no es valido o ya vencio.")
        return render(request, self.template_name, {"form": ClientPortalAccessForm()})

    def post(self, request):
        identity = request.POST.get("identifier", "")
        if not ensure_not_rate_limited(request, "portal-access", identity):
            return render(request, self.template_name, {"form": ClientPortalAccessForm(request.POST)})
        form = ClientPortalAccessForm(request.POST)
        if form.is_valid():
            customer = self.authenticate_customer(
                company=self.get_company(),
                identifier=form.cleaned_data["identifier"],
                phone=form.cleaned_data["phone"],
            )
            if customer:
                clear_rate_limit("portal-access", request, form.cleaned_data["identifier"])
                request.session[PORTAL_SESSION_KEY] = customer.pk
                request.session.pop(PORTAL_ACCOUNT_SESSION_KEY, None)
                request.session.set_expiry(60 * 60 * 8)
                messages.success(request, f"Bienvenido, {customer.full_name}.")
                return redirect("portal-dashboard")
            record_rate_limit_failure("portal-access", request, form.cleaned_data["identifier"])
            messages.error(request, "No encontramos un cliente que coincida con esos datos.")
        else:
            record_rate_limit_failure("portal-access", request, identity)
        return render(request, self.template_name, {"form": form})

    def authenticate_customer(self, company, identifier, phone):
        if not company:
            return None
        return authenticate_customer_identity(company, identifier, phone)

    def authenticate_by_token(self, company, token):
        if not company:
            return None
        customer_id = resolve_portal_access_token(token)
        if not customer_id:
            return None
        return Customer.objects.filter(company=company, pk=customer_id, is_deleted=False).first()


class ClientPortalLoginView(View):
    template_name = "portal/login.html"

    def get(self, request):
        if request.session.get(PORTAL_ACCOUNT_SESSION_KEY):
            return redirect("portal-dashboard")
        return render(request, self.template_name, {"form": ClientPortalLoginForm()})

    def post(self, request):
        identity = request.POST.get("email_login", "")
        if not ensure_not_rate_limited(request, "portal-login", identity):
            return render(request, self.template_name, {"form": ClientPortalLoginForm(request.POST)})
        form = ClientPortalLoginForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data["account"]
            clear_rate_limit("portal-login", request, form.cleaned_data["email_login"])
            request.session[PORTAL_ACCOUNT_SESSION_KEY] = account.pk
            request.session.pop(PORTAL_SESSION_KEY, None)
            request.session.set_expiry(60 * 60 * 12)
            account.mark_logged_in()
            messages.success(request, f"Bienvenido al portal, {account.customer.full_name}.")
            return redirect("portal-dashboard")
        record_rate_limit_failure("portal-login", request, identity)
        return render(request, self.template_name, {"form": form})


class ClientPortalRegisterView(View):
    template_name = "portal/register.html"

    def get_company(self):
        return Company.objects.filter(is_active=True).order_by("id").first()

    def get(self, request):
        token = request.GET.get("token")
        invited_customer = self.resolve_invited_customer(token)
        if invited_customer:
            return render(
                request,
                self.template_name,
                {"form": ClientPortalInviteRegistrationForm(), "invited_customer": invited_customer, "invite_token": token},
            )
        return render(request, self.template_name, {"form": ClientPortalRegistrationForm()})

    def post(self, request):
        token = request.POST.get("invite_token")
        invited_customer = self.resolve_invited_customer(token)
        if invited_customer:
            identity = request.POST.get("email_login", invited_customer.full_name)
            if not ensure_not_rate_limited(request, "portal-register", identity):
                return render(
                    request,
                    self.template_name,
                    {"form": ClientPortalInviteRegistrationForm(request.POST), "invited_customer": invited_customer, "invite_token": token},
                )
            form = ClientPortalInviteRegistrationForm(request.POST)
            if form.is_valid():
                result = self.create_account(invited_customer, form.cleaned_data["email_login"], form.cleaned_data["password1"])
                if result["error"]:
                    record_rate_limit_failure("portal-register", request, identity)
                    form.add_error("email_login", result["error"])
                    return render(
                        request,
                        self.template_name,
                        {"form": form, "invited_customer": invited_customer, "invite_token": token},
                    )
                clear_rate_limit("portal-register", request, form.cleaned_data["email_login"])
                self.login_account(request, result["account"])
                messages.success(request, "Tu cuenta portal fue creada correctamente.")
                return redirect("portal-dashboard")
            record_rate_limit_failure("portal-register", request, identity)
            return render(
                request,
                self.template_name,
                {"form": form, "invited_customer": invited_customer, "invite_token": token},
            )

        identity = request.POST.get("email_login", request.POST.get("identifier", ""))
        if not ensure_not_rate_limited(request, "portal-register", identity):
            return render(request, self.template_name, {"form": ClientPortalRegistrationForm(request.POST)})
        form = ClientPortalRegistrationForm(request.POST)
        if form.is_valid():
            customer = authenticate_customer_identity(
                self.get_company(),
                form.cleaned_data["identifier"],
                form.cleaned_data["phone"],
            )
            if not customer:
                record_rate_limit_failure("portal-register", request, identity)
                form.add_error("identifier", "No pudimos validar el cliente con esos datos.")
                return render(request, self.template_name, {"form": form})
            result = self.create_account(customer, form.cleaned_data["email_login"], form.cleaned_data["password1"])
            if result["error"]:
                record_rate_limit_failure("portal-register", request, identity)
                form.add_error("email_login", result["error"])
                return render(request, self.template_name, {"form": form})
            clear_rate_limit("portal-register", request, form.cleaned_data["email_login"])
            self.login_account(request, result["account"])
            messages.success(request, "Tu cuenta portal fue creada correctamente.")
            return redirect("portal-dashboard")
        record_rate_limit_failure("portal-register", request, identity)
        return render(request, self.template_name, {"form": form})

    def resolve_invited_customer(self, token):
        if not token:
            return None
        customer_id = resolve_portal_register_token(token)
        if not customer_id:
            return None
        company = self.get_company()
        return Customer.objects.filter(company=company, pk=customer_id, is_deleted=False).first()

    def create_account(self, customer, email_login, password):
        if hasattr(customer, "portal_account"):
            return {"account": None, "error": "Ese cliente ya tiene una cuenta portal creada."}
        if CustomerPortalAccount.objects.filter(email_login__iexact=email_login).exists():
            return {"account": None, "error": "Ese correo ya esta en uso en otra cuenta portal."}
        account = CustomerPortalAccount(
            customer=customer,
            email_login=email_login,
            is_active=True,
            is_verified=True,
        )
        account.set_password(password)
        account.save()
        if not customer.email:
            customer.email = email_login
            customer.save(update_fields=["email", "updated_at"])
        return {"account": account, "error": ""}

    def login_account(self, request, account):
        request.session[PORTAL_ACCOUNT_SESSION_KEY] = account.pk
        request.session.pop(PORTAL_SESSION_KEY, None)
        request.session.set_expiry(60 * 60 * 12)
        account.mark_logged_in()


class ClientPortalRecoveryView(View):
    template_name = "portal/recover.html"

    def get_company(self):
        return Company.objects.filter(is_active=True).order_by("id").first()

    def get(self, request):
        return render(request, self.template_name, {"form": ClientPortalRecoveryForm()})

    def post(self, request):
        identity = request.POST.get("email_login", request.POST.get("identifier", ""))
        if not ensure_not_rate_limited(request, "portal-recover", identity):
            return render(request, self.template_name, {"form": ClientPortalRecoveryForm(request.POST)})
        form = ClientPortalRecoveryForm(request.POST)
        if form.is_valid():
            customer = authenticate_customer_identity(
                self.get_company(),
                form.cleaned_data["identifier"],
                form.cleaned_data["phone"],
            )
            if not customer or not hasattr(customer, "portal_account"):
                record_rate_limit_failure("portal-recover", request, identity)
                form.add_error("identifier", "No encontramos una cuenta portal asociada a esos datos.")
                return render(request, self.template_name, {"form": form})
            account = customer.portal_account
            if account.email_login.lower() != form.cleaned_data["email_login"].lower():
                record_rate_limit_failure("portal-recover", request, identity)
                form.add_error("email_login", "El correo no coincide con la cuenta portal registrada.")
                return render(request, self.template_name, {"form": form})
            account.set_password(form.cleaned_data["password1"])
            account.save(update_fields=["password_hash", "updated_at"])
            clear_rate_limit("portal-recover", request, form.cleaned_data["email_login"])
            request.session[PORTAL_ACCOUNT_SESSION_KEY] = account.pk
            request.session.pop(PORTAL_SESSION_KEY, None)
            request.session.set_expiry(60 * 60 * 12)
            account.mark_logged_in()
            messages.success(request, "Tu contrasena fue actualizada correctamente.")
            return redirect("portal-dashboard")
        record_rate_limit_failure("portal-recover", request, identity)
        return render(request, self.template_name, {"form": form})


class ClientPortalDashboardView(ClientPortalSessionMixin, View):
    template_name = "portal/dashboard.html"

    def get(self, request):
        context = self.build_customer_context()
        return render(request, self.template_name, context)


class ClientPortalInvoiceListView(ClientPortalSessionMixin, View):
    template_name = "portal/invoices.html"

    def get(self, request):
        context = self.build_customer_context()
        customer = context["portal_customer"]
        context["invoices"] = Invoice.objects.filter(company=customer.company, customer=customer, is_deleted=False).order_by("-issue_date")
        return render(request, self.template_name, context)


class ClientPortalPaymentListView(ClientPortalSessionMixin, View):
    template_name = "portal/payments.html"

    def get(self, request):
        context = self.build_customer_context()
        customer = context["portal_customer"]
        context["payments"] = Payment.objects.filter(company=customer.company, customer=customer, is_deleted=False).order_by("-paid_at")
        return render(request, self.template_name, context)


class ClientPortalLogoutView(View):
    def post(self, request):
        request.session.pop(PORTAL_SESSION_KEY, None)
        request.session.pop(PORTAL_ACCOUNT_SESSION_KEY, None)
        messages.success(request, "Sesion del portal cerrada correctamente.")
        return redirect(reverse("portal-access"))
