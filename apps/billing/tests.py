from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.billing.models import Currency, Invoice, Payment
from apps.billing.services import generate_invoice_for_customer, reactivate_customer, suspend_customer_for_nonpayment
from apps.core.models import Company, SystemSetting
from apps.customers.models import Customer
from apps.services_app.models import CustomerService, ServicePlan


class BillingFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("tester")
        self.company = Company.objects.create(name="QvaTel")
        SystemSetting.objects.create(company=self.company, invoice_prefix="QVT")
        self.currency = Currency.objects.create(code="USD", name="Dolar")
        self.customer = Customer.objects.create(company=self.company, full_name="Cliente Demo", status=Customer.Status.ACTIVE)
        self.plan = ServicePlan.objects.create(company=self.company, name="Plan 20M", monthly_price=Decimal("30.00"))
        self.service = CustomerService.objects.create(
            company=self.company,
            customer=self.customer,
            plan=self.plan,
            start_date=date.today(),
            monthly_price=Decimal("30.00"),
        )

    def test_invoice_generation_uses_service_price(self):
        invoice = generate_invoice_for_customer(self.customer, created_by=self.user)
        self.assertEqual(invoice.subtotal, Decimal("30.00"))
        self.assertEqual(invoice.balance_due, Decimal("30.00"))

    def test_payment_marks_invoice_paid(self):
        invoice = generate_invoice_for_customer(self.customer, created_by=self.user)
        payment = Payment.objects.create(
            company=self.company,
            customer=self.customer,
            invoice=invoice,
            amount=Decimal("30.00"),
            currency=self.currency,
        )
        payment.apply()
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_suspend_and_reactivate_changes_customer_status(self):
        suspend_customer_for_nonpayment(self.customer, self.user)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, Customer.Status.SUSPENDED)
        reactivate_customer(self.customer, self.user)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, Customer.Status.ACTIVE)
