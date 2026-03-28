from apps.core.models import Company, SystemSetting
from apps.core.services import build_setup_wizard


def system_context(request):
    company = Company.objects.filter(is_active=True).order_by("id").first()
    setup_wizard = build_setup_wizard(company)
    onboarding_mode = bool(
        setup_wizard["is_needed"]
        and (
            request.path.startswith("/setup/")
            or request.path == "/setup/"
            or request.path.startswith("/settings/reset/")
        )
    )
    return {
        "system_company": company,
        "system_settings": SystemSetting.load(),
        "global_setup_wizard": setup_wizard,
        "global_onboarding_mode": onboarding_mode,
    }
