from celery import shared_task
from django.utils import timezone

from apps.billing.services import generate_monthly_invoices, mark_overdue_invoices, suspend_customer_for_nonpayment
from apps.billing.models import Invoice
from apps.core.models import Company, SystemSetting


@shared_task
def generate_monthly_invoices_task():
    company = Company.objects.filter(is_active=True).first()
    return len(generate_monthly_invoices(company))


@shared_task
def mark_overdue_invoices_task():
    return mark_overdue_invoices()


@shared_task
def send_due_reminders_task():
    company = Company.objects.filter(is_active=True).first()
    setting = SystemSetting.objects.filter(company=company).first()
    if not setting:
        return 0
    target_date = timezone.localdate() + timezone.timedelta(days=setting.reminder_days_before_due)
    return Invoice.objects.filter(company=company, due_date=target_date, status=Invoice.Status.ISSUED, is_deleted=False).count()


@shared_task
def auto_suspend_overdue_customers_task():
    company = Company.objects.filter(is_active=True).first()
    setting = SystemSetting.objects.filter(company=company).first()
    if not setting:
        return 0
    target_date = timezone.localdate() - timezone.timedelta(days=setting.suspension_days_after_due)
    count = 0
    overdue_invoices = Invoice.objects.filter(company=company, due_date__lte=target_date, balance_due__gt=0, is_deleted=False).select_related("customer")
    for invoice in overdue_invoices:
        if invoice.customer.status != invoice.customer.Status.SUSPENDED:
            suspend_customer_for_nonpayment(invoice.customer, None, "Suspension automatica por mora")
            count += 1
    return count
