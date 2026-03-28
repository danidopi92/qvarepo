import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse
from django.views.generic import TemplateView
from openpyxl import Workbook

from apps.billing.models import Invoice, Payment
from apps.core.models import Company
from apps.customers.models import Customer


class ReportsHomeView(LoginRequiredMixin, TemplateView):
    template_name = "reports/index.html"

    def get_company(self):
        return Company.objects.filter(is_active=True).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        context["debtor_count"] = Invoice.objects.filter(company=company, status=Invoice.Status.OVERDUE, is_deleted=False).count()
        context["month_income"] = Payment.objects.filter(company=company, is_deleted=False).aggregate(total=Sum("amount"))["total"] or 0
        return context


def export_debtors_csv(_request):
    company = Company.objects.filter(is_active=True).first()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="morosos.csv"'
    writer = csv.writer(response)
    writer.writerow(["Cliente", "Factura", "Vence", "Saldo"])
    for invoice in Invoice.objects.filter(company=company, status=Invoice.Status.OVERDUE, is_deleted=False).select_related("customer"):
        writer.writerow([invoice.customer.full_name, invoice.invoice_number, invoice.due_date, invoice.balance_due])
    return response


def export_income_excel(_request):
    company = Company.objects.filter(is_active=True).first()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ingresos"
    sheet.append(["Cliente", "Factura", "Metodo", "Monto", "Fecha"])
    for payment in Payment.objects.filter(company=company, is_deleted=False).select_related("customer", "invoice"):
        sheet.append([payment.customer.full_name, getattr(payment.invoice, "invoice_number", ""), payment.get_method_display(), float(payment.amount), payment.paid_at.strftime("%Y-%m-%d %H:%M")])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="ingresos.xlsx"'
    workbook.save(response)
    return response


def export_customers_csv(_request):
    company = Company.objects.filter(is_active=True).first()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="clientes.csv"'
    writer = csv.writer(response)
    writer.writerow(["Nombre", "Telefono", "Email", "Nodo", "Estado", "IP"])
    for customer in Customer.objects.filter(company=company, is_deleted=False).select_related("node"):
        writer.writerow([customer.full_name, customer.phone, customer.email, customer.node.name if customer.node else "", customer.get_status_display(), customer.assigned_ip or ""])
    return response
