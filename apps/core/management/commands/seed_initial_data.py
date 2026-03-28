from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.billing.models import Currency
from apps.core.models import Company, SystemSetting
from apps.core.services import bootstrap_roles
from apps.customers.models import Node
from apps.services_app.models import ServicePlan


class Command(BaseCommand):
    help = "Carga datos iniciales del sistema"

    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(name="QvaTel", defaults={"legal_name": "QvaTel ISP"})
        SystemSetting.objects.get_or_create(company=company)
        bootstrap_roles()

        for code, name in [("USD", "Dolar estadounidense"), ("EUR", "Euro"), ("CUP", "Peso cubano")]:
            Currency.objects.get_or_create(code=code, defaults={"name": name})

        node, _ = Node.objects.get_or_create(company=company, name="Nodo Central", defaults={"zone": "Centro"})
        ServicePlan.objects.get_or_create(
            company=company,
            name="Residencial 20M",
            defaults={"service_type": ServicePlan.ServiceType.INTERNET, "speed_label": "20 Mbps", "monthly_price": Decimal("25.00")},
        )
        ServicePlan.objects.get_or_create(
            company=company,
            name="Empresarial 50M",
            defaults={"service_type": ServicePlan.ServiceType.INTERNET, "speed_label": "50 Mbps", "monthly_price": Decimal("75.00")},
        )

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@qvatel.local", "admin12345")

        self.stdout.write(self.style.SUCCESS(f"Datos iniciales creados para {company.name} con nodo {node.name}"))
