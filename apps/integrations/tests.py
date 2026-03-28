from django.test import TestCase, override_settings

from apps.core.models import Company
from apps.customers.models import Customer
from apps.integrations.models import IntegrationEvent
from apps.integrations.services import OpenClawGateway


@override_settings(OPENCLAW_SIMULATION_MODE=True)
class OpenClawGatewayTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="QvaTel")
        self.customer = Customer.objects.create(company=self.company, full_name="Cliente Simulado")

    def test_simulation_creates_integration_event(self):
        result = OpenClawGateway().suspend_customer(self.customer)
        self.assertTrue(result["success"])
        self.assertTrue(IntegrationEvent.objects.filter(customer=self.customer, action="suspend-customer").exists())
