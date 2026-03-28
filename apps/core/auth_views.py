from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

from apps.core.models import Company
from apps.core.services import build_setup_wizard

from apps.core.security import clear_rate_limit, is_rate_limited, record_rate_limit_failure


class RateLimitedLoginView(LoginView):
    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):
        company = Company.objects.filter(is_active=True).order_by("id").first()
        if build_setup_wizard(company)["is_needed"]:
            return redirect("setup-wizard")
        return super().dispatch(request, *args, **kwargs)

    def get_identity(self):
        return self.request.POST.get("username", "")

    def post(self, request, *args, **kwargs):
        if is_rate_limited("staff-login", request, self.get_identity()):
            messages.error(request, "Demasiados intentos de acceso. Espera unos minutos antes de volver a probar.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        clear_rate_limit("staff-login", self.request, self.get_identity())
        return super().form_valid(form)

    def form_invalid(self, form):
        record_rate_limit_failure("staff-login", self.request, self.get_identity())
        return super().form_invalid(form)
