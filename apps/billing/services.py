from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import Currency, Invoice, InvoiceItem, SuspensionEvent
from apps.core.models import Company, SystemSetting
from apps.customers.models import Customer
from apps.integrations.services import OpenClawGateway
from apps.services_app.models import CustomerService


def get_default_company():
    return Company.objects.filter(is_active=True).first()


@transaction.atomic
def generate_invoice_for_customer(customer, issue_date=None, due_date=None, created_by=None):
    company = customer.company
    issue_date = issue_date or timezone.localdate()
    settings = SystemSetting.objects.get(company=company)
    due_date = due_date or (issue_date + timezone.timedelta(days=settings.payment_grace_days))
    currency = Currency.objects.filter(code=company.default_currency).first() or Currency.objects.first()

    invoice = Invoice.objects.create(
        company=company,
        customer=customer,
        invoice_number=Invoice.next_invoice_number(company),
        issue_date=issue_date,
        due_date=due_date,
        currency=currency,
        created_by=created_by,
        updated_by=created_by,
    )

    subtotal = Decimal("0.00")
    for service in CustomerService.objects.filter(customer=customer, status=CustomerService.Status.ACTIVE, is_deleted=False):
        InvoiceItem.objects.create(
            company=company,
            invoice=invoice,
            service=service,
            description=f"{service.plan.name} - {issue_date.strftime('%B %Y')}",
            quantity=Decimal("1.00"),
            unit_price=service.monthly_price,
            created_by=created_by,
            updated_by=created_by,
        )
        subtotal += service.monthly_price

    invoice.subtotal = subtotal
    invoice.tax_amount = (subtotal * settings.default_tax_percent) / Decimal("100.00")
    invoice.save()
    return invoice


def generate_monthly_invoices(company=None):
    company = company or get_default_company()
    created = []
    for customer in Customer.objects.filter(company=company, status=Customer.Status.ACTIVE, is_deleted=False):
        if not customer.services.filter(status=CustomerService.Status.ACTIVE, is_deleted=False).exists():
            continue
        issue_date = timezone.localdate().replace(day=1)
        if Invoice.objects.filter(customer=customer, issue_date=issue_date, is_deleted=False).exists():
            continue
        created.append(generate_invoice_for_customer(customer, issue_date=issue_date))
    return created


def mark_overdue_invoices():
    updated = 0
    for invoice in Invoice.objects.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.DRAFT], is_deleted=False):
        previous = invoice.status
        invoice.save()
        if invoice.status != previous:
            updated += 1
    return updated


def suspend_customer_for_nonpayment(customer, user=None, reason="Suspension automatica por impago"):
    customer.status = Customer.Status.SUSPENDED
    customer.updated_by = user
    customer.save(update_fields=["status", "updated_by", "updated_at"])
    for service in customer.services.filter(is_deleted=False):
        service.status = CustomerService.Status.SUSPENDED
        service.updated_by = user
        service.save(update_fields=["status", "updated_by", "updated_at"])
    event = SuspensionEvent.objects.create(
        company=customer.company,
        customer=customer,
        action=SuspensionEvent.Action.SUSPEND,
        reason=reason,
        created_by=user,
        updated_by=user,
    )
    gateway = OpenClawGateway()
    response = gateway.suspend_customer(customer)
    event.technical_executed = response.get("success", False)
    event.integration_reference = response.get("reference", "")
    event.notes = response.get("summary", "")
    event.save(update_fields=["technical_executed", "integration_reference", "notes", "updated_at"])
    return event


def reactivate_customer(customer, user=None, reason="Reactivacion por pago"):
    customer.status = Customer.Status.ACTIVE
    customer.updated_by = user
    customer.save(update_fields=["status", "updated_by", "updated_at"])
    for service in customer.services.filter(is_deleted=False):
        service.status = CustomerService.Status.ACTIVE
        service.updated_by = user
        service.save(update_fields=["status", "updated_by", "updated_at"])
    event = SuspensionEvent.objects.create(
        company=customer.company,
        customer=customer,
        action=SuspensionEvent.Action.REACTIVATE,
        reason=reason,
        created_by=user,
        updated_by=user,
    )
    gateway = OpenClawGateway()
    response = gateway.reactivate_customer(customer)
    event.technical_executed = response.get("success", False)
    event.integration_reference = response.get("reference", "")
    event.notes = response.get("summary", "")
    event.save(update_fields=["technical_executed", "integration_reference", "notes", "updated_at"])
    return event
