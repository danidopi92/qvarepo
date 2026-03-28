from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.models import Company
from apps.services_app.forms import CustomerServiceForm
from apps.services_app.models import CustomerService


class CompanyMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class CustomerServiceListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = CustomerService
    template_name = "services/list.html"
    context_object_name = "services"
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomerService.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "plan", "node")
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            queryset = queryset.filter(
                Q(customer__full_name__icontains=query)
                | Q(plan__name__icontains=query)
                | Q(node__name__icontains=query)
                | Q(pppoe_username__icontains=query)
                | Q(mac_address__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_statuses"] = CustomerService.Status.choices
        return context


class CustomerServiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, CreateView):
    permission_required = "services_app.add_customerservice"
    model = CustomerService
    form_class = CustomerServiceForm
    template_name = "services/form.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("customer"):
            initial["customer"] = self.request.GET.get("customer")
        return initial

    def form_valid(self, form):
        form.instance.company = self.get_company()
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Servicio asignado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.customer.get_absolute_url()


class CustomerServiceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, UpdateView):
    permission_required = "services_app.change_customerservice"
    model = CustomerService
    form_class = CustomerServiceForm
    template_name = "services/form.html"

    def get_queryset(self):
        return CustomerService.objects.filter(company=self.get_company(), is_deleted=False)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Servicio actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.customer.get_absolute_url()
