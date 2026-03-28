from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.billing.models import Currency, Invoice, Payment
from apps.client_portal.models import CustomerPortalAccount
from apps.client_portal.services import build_portal_register_token
from apps.core.models import Company, SystemSetting
from apps.customers.models import Customer
from apps.services_app.models import CustomerService, ServicePlan


class ClientPortalTests(TestCase):
    def setUp(self):
        cache.clear()
        self.company = Company.objects.create(name="QvaTel")
        SystemSetting.objects.create(company=self.company)
        self.currency = Currency.objects.create(code="USD", name="Dolar")
        self.customer = Customer.objects.create(
            company=self.company,
            full_name="Cliente Portal",
            document_id="ABC123",
            phone="+53 55512345",
            whatsapp="+53 55512345",
        )
        self.plan = ServicePlan.objects.create(
            company=self.company,
            name="Internet 30M",
            speed_label="30 Mbps",
            monthly_price=Decimal("35.00"),
        )
        CustomerService.objects.create(
            company=self.company,
            customer=self.customer,
            plan=self.plan,
            monthly_price=Decimal("35.00"),
            start_date=date.today(),
        )
        self.invoice = Invoice.objects.create(
            company=self.company,
            customer=self.customer,
            invoice_number="QVT-000001",
            due_date=date.today(),
            subtotal=Decimal("35.00"),
            total_amount=Decimal("35.00"),
            balance_due=Decimal("35.00"),
            currency=self.currency,
        )
        Payment.objects.create(
            company=self.company,
            customer=self.customer,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            currency=self.currency,
            method=Payment.Method.PAYPAL,
        )

    def test_access_view_authenticates_customer(self):
        response = self.client.post(reverse("portal-access"), {"identifier": "ABC123", "phone": "12345"})
        self.assertRedirects(response, reverse("portal-dashboard"))

    def test_dashboard_requires_session(self):
        response = self.client.get(reverse("portal-dashboard"))
        self.assertRedirects(response, reverse("portal-access"))

    def test_dashboard_shows_customer_after_login(self):
        session = self.client.session
        session["client_portal_customer_id"] = self.customer.pk
        session.save()
        response = self.client.get(reverse("portal-dashboard"))
        self.assertContains(response, "Cliente Portal")
        self.assertContains(response, "Internet 30M")

    def test_secure_token_access_logs_customer_in(self):
        from apps.client_portal.services import build_portal_access_token

        token = build_portal_access_token(self.customer)
        response = self.client.get(f"{reverse('portal-access')}?token={token}")
        self.assertRedirects(response, reverse("portal-dashboard"))

    def test_register_creates_portal_account(self):
        response = self.client.post(
            reverse("portal-register"),
            {
                "identifier": "ABC123",
                "phone": "12345",
                "email_login": "cliente@correo.com",
                "password1": "segura123",
                "password2": "segura123",
            },
        )
        self.assertRedirects(response, reverse("portal-dashboard"))
        self.assertTrue(CustomerPortalAccount.objects.filter(customer=self.customer, email_login="cliente@correo.com").exists())

    def test_login_with_portal_account(self):
        account = CustomerPortalAccount.objects.create(customer=self.customer, email_login="cliente@correo.com")
        account.set_password("segura123")
        account.save()

        response = self.client.post(
            reverse("portal-login"),
            {"email_login": "cliente@correo.com", "password": "segura123"},
        )
        self.assertRedirects(response, reverse("portal-dashboard"))

    def test_recover_updates_password(self):
        account = CustomerPortalAccount.objects.create(customer=self.customer, email_login="cliente@correo.com")
        account.set_password("segura123")
        account.save()

        response = self.client.post(
            reverse("portal-recover"),
            {
                "identifier": "ABC123",
                "phone": "12345",
                "email_login": "cliente@correo.com",
                "password1": "nueva1234",
                "password2": "nueva1234",
            },
        )
        self.assertRedirects(response, reverse("portal-dashboard"))
        account.refresh_from_db()
        self.assertTrue(account.check_password("nueva1234"))

    def test_invitation_token_registers_account(self):
        token = build_portal_register_token(self.customer)
        response = self.client.post(
            reverse("portal-register"),
            {
                "invite_token": token,
                "email_login": "invitado@correo.com",
                "password1": "segura123",
                "password2": "segura123",
            },
        )
        self.assertRedirects(response, reverse("portal-dashboard"))
        self.assertTrue(CustomerPortalAccount.objects.filter(customer=self.customer, email_login="invitado@correo.com").exists())

    def test_inactive_account_cannot_login(self):
        account = CustomerPortalAccount.objects.create(
            customer=self.customer,
            email_login="cliente@correo.com",
            is_active=False,
        )
        account.set_password("segura123")
        account.save()

        response = self.client.post(
            reverse("portal-login"),
            {"email_login": "cliente@correo.com", "password": "segura123"},
        )
        self.assertContains(response, "desactivada")

    @override_settings(AUTH_RATE_LIMIT_ATTEMPTS=1, AUTH_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_portal_login_rate_limit_blocks_second_attempt(self):
        response = self.client.post(
            reverse("portal-login"),
            {"email_login": "nadie@correo.com", "password": "incorrecta"},
        )
        self.assertEqual(response.status_code, 200)

        blocked = self.client.post(
            reverse("portal-login"),
            {"email_login": "nadie@correo.com", "password": "incorrecta"},
        )
        self.assertContains(blocked, "Demasiados intentos")
