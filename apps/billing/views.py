from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.billing.forms import InvoiceForm, InvoiceItemFormSet, PaymentForm
from apps.billing.models import Invoice, Payment
from apps.billing.services import generate_monthly_invoices, reactivate_customer, suspend_customer_for_nonpayment
from apps.core.models import Company
from apps.customers.models import Customer


class CompanyMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class InvoiceListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        queryset = Invoice.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "currency")
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            queryset = queryset.filter(
                Q(invoice_number__icontains=query)
                | Q(customer__full_name__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoices = self.get_queryset()
        context["invoice_statuses"] = Invoice.Status.choices
        context["invoice_summary"] = {
            "count": invoices.count(),
            "total": invoices.aggregate(total=Sum("total_amount"))["total"] or 0,
            "pending": invoices.aggregate(total=Sum("balance_due"))["total"] or 0,
        }
        return context


class InvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "billing.add_invoice"
    template_name = "billing/invoice_form.html"

    def get(self, request):
        initial = {}
        if request.GET.get("customer"):
            initial["customer"] = request.GET.get("customer")
        form = InvoiceForm(initial=initial)
        formset = InvoiceItemFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.company = self.get_company()
            invoice.invoice_number = Invoice.next_invoice_number(self.get_company())
            invoice.created_by = request.user
            invoice.updated_by = request.user
            invoice.save()
            formset.instance = invoice
            items = formset.save(commit=False)
            subtotal = 0
            for item in items:
                item.company = self.get_company()
                item.created_by = request.user
                item.updated_by = request.user
                item.save()
                subtotal += item.line_total
            invoice.subtotal = subtotal
            invoice.save()
            messages.success(request, f"Factura {invoice.invoice_number} creada.")
            return redirect("invoice-detail", pk=invoice.pk)
        return render(request, self.template_name, {"form": form, "formset": formset})


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return Invoice.objects.filter(is_deleted=False).select_related("customer", "currency")


class PaymentListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Payment
    template_name = "billing/payment_list.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        queryset = Payment.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "invoice", "currency")
        query = self.request.GET.get("q")
        method = self.request.GET.get("method")
        if query:
            queryset = queryset.filter(
                Q(reference__icontains=query)
                | Q(customer__full_name__icontains=query)
                | Q(invoice__invoice_number__icontains=query)
            )
        if method:
            queryset = queryset.filter(method=method)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context["today_total"] = queryset.filter(paid_at__date=timezone.localdate()).aggregate(total=Sum("amount"))["total"] or 0
        context["payment_methods"] = Payment.Method.choices
        context["payment_count"] = queryset.count()
        return context


class PaymentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, CreateView):
    permission_required = "billing.add_payment"
    model = Payment
    form_class = PaymentForm
    template_name = "billing/payment_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("customer"):
            initial["customer"] = self.request.GET.get("customer")
        if self.request.GET.get("invoice"):
            initial["invoice"] = self.request.GET.get("invoice")
        return initial

    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.company = self.get_company()
        payment.registered_by = self.request.user
        payment.created_by = self.request.user
        payment.updated_by = self.request.user
        payment.save()
        payment.apply()
        if payment.invoice and payment.invoice.status == Invoice.Status.PAID and payment.customer.status == Customer.Status.SUSPENDED:
            reactivate_customer(payment.customer, self.request.user, "Reactivacion automatica tras pago")
        messages.success(self.request, "Pago registrado correctamente.")
        return redirect("customer-detail", pk=payment.customer.pk)


class BillingGenerateMonthlyView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "billing.add_invoice"

    def post(self, request):
        invoices = generate_monthly_invoices(self.get_company())
        messages.success(request, f"Facturacion mensual generada. Facturas creadas: {len(invoices)}.")
        return redirect("invoice-list")


class DebtorsReportView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Invoice
    template_name = "billing/debtors.html"
    context_object_name = "invoices"

    def get_queryset(self):
        return Invoice.objects.filter(company=self.get_company(), status=Invoice.Status.OVERDUE, is_deleted=False).select_related("customer")


class SuspendCustomerView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "billing.add_suspensionevent"

    def post(self, request, customer_id):
        customer = get_object_or_404(Customer, pk=customer_id, company=self.get_company(), is_deleted=False)
        reason = request.POST.get("reason", "Suspension manual por impago")
        suspend_customer_for_nonpayment(customer, request.user, reason)
        messages.warning(request, "Cliente suspendido y solicitud enviada a OpenClaw.")
        return redirect("customer-detail", pk=customer.pk)


class ReactivateCustomerView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "billing.add_suspensionevent"

    def post(self, request, customer_id):
        customer = get_object_or_404(Customer, pk=customer_id, company=self.get_company(), is_deleted=False)
        reason = request.POST.get("reason", "Reactivacion manual")
        reactivate_customer(customer, request.user, reason)
        messages.success(request, "Cliente reactivado y sincronizado con OpenClaw.")
        return redirect("customer-detail", pk=customer.pk)
