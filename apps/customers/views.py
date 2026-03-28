from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Case, IntegerField, Prefetch, Sum, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from urllib.parse import quote
from openpyxl import Workbook

from apps.billing.models import Invoice, Payment, SuspensionEvent
from apps.client_portal.models import CustomerPortalAccount
from apps.client_portal.services import build_portal_access_token, build_portal_register_token
from apps.core.models import Company
from apps.core.services import log_action
from apps.customers.forms import CustomerForm, ImportCustomersForm
from apps.customers.models import Customer, Node
from apps.customers.services import assign_customer_plan, import_customers
from apps.services_app.models import CustomerService


class CompanyMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


CUSTOMER_FILTERS_SESSION_KEY = "customer_list_filters"
CUSTOMER_PAGE_SIZE_SESSION_KEY = "customer_list_page_size"
CUSTOMER_FILTER_KEYS = ["filter_field", "filter_value", "status", "node", "preferred_payment_method"]
CUSTOMER_PAGE_SIZE_OPTIONS = ["20", "50", "100", "all"]
CUSTOMER_TABLE_COLUMNS = [
    {"key": "payment_day", "label": "Dia de pago"},
    {"key": "full_name", "label": "Nombre"},
    {"key": "address", "label": "Direccion"},
    {"key": "phone", "label": "Telefono"},
    {"key": "email", "label": "Correo"},
    {"key": "node", "label": "Nodo"},
    {"key": "assigned_ip", "label": "IP"},
    {"key": "plan", "label": "Plan"},
    {"key": "preferred_payment_method", "label": "Tipo de pago"},
    {"key": "internal_notes", "label": "Notas"},
]
CUSTOMER_FILTER_FIELD_CHOICES = [
    ("global", "Busqueda global"),
    ("payment_day", "Dia de pago"),
    ("full_name", "Nombre"),
    ("address", "Direccion"),
    ("phone", "Telefono"),
    ("email", "Correo"),
    ("node", "Nodo"),
    ("assigned_ip", "IP"),
    ("plan", "Plan"),
    ("preferred_payment_method", "Tipo de pago"),
    ("internal_notes", "Notas"),
]


class CustomerListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Customer
    template_name = "customers/list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_default_filters(self):
        return {key: "" for key in CUSTOMER_FILTER_KEYS}

    def get_filter_values(self):
        if self.request.GET.get("reset") == "1":
            self.request.session.pop(CUSTOMER_FILTERS_SESSION_KEY, None)
            return self.get_default_filters()

        if any(key in self.request.GET for key in CUSTOMER_FILTER_KEYS):
            filters = {key: self.request.GET.get(key, "").strip() for key in CUSTOMER_FILTER_KEYS}
            filters["filter_field"] = filters.get("filter_field") or "global"
            self.request.session[CUSTOMER_FILTERS_SESSION_KEY] = filters
            return filters

        stored_filters = self.request.session.get(CUSTOMER_FILTERS_SESSION_KEY, self.get_default_filters())
        stored_filters.setdefault("filter_field", "global")
        stored_filters.setdefault("filter_value", "")
        return stored_filters

    def get_page_size(self):
        requested_page_size = self.request.GET.get("per_page", "").strip().lower()
        if requested_page_size in CUSTOMER_PAGE_SIZE_OPTIONS:
            self.request.session[CUSTOMER_PAGE_SIZE_SESSION_KEY] = requested_page_size
            return requested_page_size

        stored_page_size = self.request.session.get(CUSTOMER_PAGE_SIZE_SESSION_KEY, str(self.paginate_by))
        if stored_page_size not in CUSTOMER_PAGE_SIZE_OPTIONS:
            stored_page_size = str(self.paginate_by)
        return stored_page_size

    def get_paginate_by(self, queryset):
        self.current_page_size = self.get_page_size()
        if self.current_page_size == "all":
            return None
        return int(self.current_page_size)

    def filter_queryset(self, queryset, filters):
        filter_field = filters.get("filter_field", "global") or "global"
        filter_value = filters.get("filter_value", "")
        status = filters.get("status", "")
        node = filters.get("node", "")
        preferred_payment_method = filters.get("preferred_payment_method", "")
        if filter_value:
            if filter_field == "global":
                queryset = queryset.filter(
                    Q(full_name__icontains=filter_value)
                    | Q(phone__icontains=filter_value)
                    | Q(email__icontains=filter_value)
                    | Q(address__icontains=filter_value)
                    | Q(internal_notes__icontains=filter_value)
                    | Q(assigned_ip__icontains=filter_value)
                    | Q(node__name__icontains=filter_value)
                    | Q(preferred_payment_method__icontains=filter_value)
                    | Q(services__plan__name__icontains=filter_value)
                ).distinct()
            elif filter_field == "payment_day":
                if filter_value.isdigit():
                    queryset = queryset.filter(payment_day=int(filter_value))
                else:
                    queryset = queryset.none()
            elif filter_field == "node":
                queryset = queryset.filter(node__name__icontains=filter_value)
            elif filter_field == "plan":
                queryset = queryset.filter(services__plan__name__icontains=filter_value).distinct()
            else:
                queryset = queryset.filter(**{f"{filter_field}__icontains": filter_value})
        if status:
            queryset = queryset.filter(status=status)
        if node:
            queryset = queryset.filter(node_id=node)
        if preferred_payment_method:
            queryset = queryset.filter(preferred_payment_method=preferred_payment_method)
        return queryset

    def get_queryset(self):
        self.current_filters = self.get_filter_values()
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=False).select_related("node").prefetch_related(
            Prefetch(
                "services",
                queryset=CustomerService.objects.filter(is_deleted=False).select_related("plan").annotate(
                    status_priority=Case(
                        When(status=CustomerService.Status.ACTIVE, then=Value(0)),
                        When(status=CustomerService.Status.PENDING, then=Value(1)),
                        When(status=CustomerService.Status.SUSPENDED, then=Value(2)),
                        default=Value(3),
                        output_field=IntegerField(),
                    )
                ).order_by("status_priority", "created_at"),
                to_attr="prefetched_services",
            )
        )
        return self.filter_queryset(queryset, self.current_filters)

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["customers/partials/customer_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Customer.Status.choices
        context["nodes"] = Node.objects.filter(company=self.get_company(), is_deleted=False).order_by("name")
        context["payment_methods"] = Customer.PreferredPaymentMethod.choices
        context["current_filters"] = getattr(self, "current_filters", self.get_filter_values())
        context["current_page_size"] = getattr(self, "current_page_size", self.get_page_size())
        context["page_size_options"] = CUSTOMER_PAGE_SIZE_OPTIONS
        context["customer_table_columns"] = CUSTOMER_TABLE_COLUMNS
        context["filter_field_choices"] = CUSTOMER_FILTER_FIELD_CHOICES
        return context


class DeletedCustomerListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Customer
    template_name = "customers/deleted_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=True).select_related("node")
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
                | Q(node__name__icontains=query)
            )
        return queryset.order_by("-deleted_at", "-updated_at")


class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, CreateView):
    permission_required = "customers.add_customer"
    model = Customer
    form_class = CustomerForm
    template_name = "customers/form.html"

    def form_valid(self, form):
        form.instance.company = self.get_company()
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Cliente creado correctamente.")
        response = super().form_valid(form)
        assign_customer_plan(form.instance, form.cleaned_data.get("service_plan"), self.request.user)
        log_action(
            company=form.instance.company,
            actor=self.request.user,
            model_name="Customer",
            object_id=form.instance.pk,
            action="created",
            changes={"full_name": form.instance.full_name},
            request_id=getattr(self.request, "request_id", ""),
        )
        return response


class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, UpdateView):
    permission_required = "customers.change_customer"
    model = Customer
    form_class = CustomerForm
    template_name = "customers/form.html"

    def get_queryset(self):
        return Customer.objects.filter(company=self.get_company(), is_deleted=False)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Cliente actualizado correctamente.")
        response = super().form_valid(form)
        assign_customer_plan(form.instance, form.cleaned_data.get("service_plan"), self.request.user)
        return response


class CustomerDetailView(LoginRequiredMixin, CompanyMixin, DetailView):
    model = Customer
    template_name = "customers/detail.html"
    context_object_name = "customer"

    def get_queryset(self):
        return Customer.objects.filter(company=self.get_company(), is_deleted=False).select_related("node")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        services = CustomerService.objects.filter(customer=customer, is_deleted=False).select_related("plan", "node")
        invoices = Invoice.objects.filter(customer=customer, is_deleted=False).order_by("-issue_date")
        context["services"] = services
        context["invoices"] = invoices
        context["payments"] = Payment.objects.filter(customer=customer, is_deleted=False).select_related("invoice")
        timeline = []
        timeline.extend(customer.notes.all()[:20])
        timeline.extend(SuspensionEvent.objects.filter(customer=customer).order_by("-created_at")[:20])
        context["timeline"] = sorted(timeline, key=lambda item: item.created_at, reverse=True)[:20]
        context["customer_summary"] = {
            "services_count": services.count(),
            "active_services": services.filter(status=CustomerService.Status.ACTIVE).count(),
            "pending_balance": invoices.aggregate(total=Sum("balance_due"))["total"] or 0,
            "overdue_invoices": invoices.filter(status=Invoice.Status.OVERDUE).count(),
        }
        context["primary_service"] = services.filter(status=CustomerService.Status.ACTIVE).first() or services.first()
        portal_code = customer.document_id or str(customer.pk)
        portal_token = build_portal_access_token(customer)
        register_token = build_portal_register_token(customer)
        secure_url = self.request.build_absolute_uri(f"{reverse('portal-access')}?token={portal_token}")
        invite_url = self.request.build_absolute_uri(f"{reverse('portal-register')}?token={register_token}")
        company_name = customer.company.name if customer.company else "QvaTel"
        access_message = (
            f"Hola {customer.full_name}, aqui tienes tu acceso al portal de clientes de {company_name}. "
            f"Puedes consultar tu plan, facturas, pagos y fecha de cobro aqui: "
            f"{secure_url}"
        )
        invite_message = (
            f"Hola {customer.full_name}, te invitamos a activar tu cuenta del portal de clientes de {company_name}. "
            f"Desde alli podras revisar tu plan, facturas, pagos y fecha de cobro. "
            f"Crea tu cuenta aqui: {invite_url}"
        )
        whatsapp_digits = "".join(ch for ch in (customer.whatsapp or customer.phone or "") if ch.isdigit())
        context["portal_access"] = {
            "recommended_code": portal_code,
            "secure_url": secure_url,
            "invite_url": invite_url,
            "manual_url": self.request.build_absolute_uri(reverse("portal-access")),
            "share_message": access_message,
            "invite_message": invite_message,
            "whatsapp_url": f"https://wa.me/{whatsapp_digits}?text={quote(access_message)}" if whatsapp_digits else "",
            "invite_whatsapp_url": f"https://wa.me/{whatsapp_digits}?text={quote(invite_message)}" if whatsapp_digits else "",
            "email_url": (
                f"mailto:{customer.email}?subject={quote(f'Acceso al portal de clientes de {company_name}')}"
                f"&body={quote(access_message)}"
            )
            if customer.email
            else "",
            "invite_email_url": (
                f"mailto:{customer.email}?subject={quote(f'Invitacion al portal de clientes de {company_name}')}"
                f"&body={quote(invite_message)}"
            )
            if customer.email
            else "",
        }
        context["portal_account"] = getattr(customer, "portal_account", None)
        return context


class CustomerImportView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.add_customer"
    template_name = "customers/import.html"
    form_class = ImportCustomersForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            results = import_customers(self.get_company(), form.cleaned_data["file"], request.user)
            messages.success(
                request,
                f"Importacion completada. Creados: {results['created']} | Actualizados: {results['updated']} | Omitidos: {results['skipped']}.",
            )
            for error in results["errors"][:10]:
                messages.warning(request, error)
            return redirect("customer-list")
        return render(request, self.template_name, {"form": form})


class CustomerExportTemplateView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.view_customer"

    def get(self, request):
        company = self.get_company()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "clientes"
        headers = [
            "customer_type",
            "full_name",
            "document_id",
            "phone",
            "whatsapp",
            "email",
            "address",
            "location_reference",
            "node",
            "assigned_ip",
            "service_plan",
            "payment_day",
            "preferred_payment_method",
            "status",
            "internal_notes",
            "tags",
        ]
        sheet.append(headers)

        queryset = Customer.objects.filter(company=company, is_deleted=False).select_related("node").prefetch_related(
            Prefetch(
                "services",
                queryset=CustomerService.objects.filter(is_deleted=False).select_related("plan").annotate(
                    status_priority=Case(
                        When(status=CustomerService.Status.ACTIVE, then=Value(0)),
                        When(status=CustomerService.Status.PENDING, then=Value(1)),
                        When(status=CustomerService.Status.SUSPENDED, then=Value(2)),
                        default=Value(3),
                        output_field=IntegerField(),
                    )
                ).order_by("status_priority", "created_at"),
                to_attr="prefetched_services",
            )
        )

        for customer in queryset:
            primary_service = customer.prefetched_services[0] if getattr(customer, "prefetched_services", None) else None
            sheet.append([
                customer.customer_type,
                customer.full_name,
                customer.document_id,
                customer.phone,
                customer.whatsapp,
                customer.email,
                customer.address,
                customer.location_reference,
                customer.node.name if customer.node else "",
                customer.assigned_ip or "",
                primary_service.plan.name if primary_service else "",
                customer.payment_day or "",
                customer.preferred_payment_method,
                customer.status,
                customer.internal_notes,
                customer.tags,
            ])

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="clientes_plantilla_{date.today().isoformat()}.xlsx"'
        workbook.save(response)
        return response


class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.delete_customer"

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, company=self.get_company(), is_deleted=False)
        customer.soft_delete(request.user)
        messages.success(request, "Cliente enviado a eliminados.")
        return redirect("customer-list")


class CustomerBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.delete_customer"

    def post(self, request):
        selected_ids = request.POST.getlist("customer_ids")
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=False)
        if not selected_ids:
            messages.warning(request, "Selecciona al menos un cliente para eliminar.")
            return redirect("customer-list")

        customers = queryset.filter(pk__in=selected_ids)
        deleted_count = 0
        for customer in customers:
            customer.soft_delete(request.user)
            deleted_count += 1

        messages.success(request, f"Clientes enviados a eliminados: {deleted_count}.")
        return redirect("customer-list")


class CustomerBulkDeleteFilteredView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.delete_customer"

    def post(self, request):
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=False).select_related("node")
        filters = {key: request.POST.get(key, "").strip() for key in CUSTOMER_FILTER_KEYS}
        queryset = CustomerListView().filter_queryset(queryset, filters)

        deleted_count = 0
        for customer in queryset:
            customer.soft_delete(request.user)
            deleted_count += 1

        messages.success(request, f"Clientes filtrados enviados a eliminados: {deleted_count}.")
        return redirect("customer-list")


class CustomerRestoreView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.change_customer"

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, company=self.get_company(), is_deleted=True)
        customer.restore()
        messages.success(request, "Cliente restaurado correctamente.")
        return redirect("customer-deleted-list")


class CustomerBulkRestoreView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.change_customer"

    def post(self, request):
        selected_ids = request.POST.getlist("customer_ids")
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=True)
        if not selected_ids:
            messages.warning(request, "Selecciona al menos un cliente para restaurar.")
            return redirect("customer-deleted-list")

        restored_count = 0
        for customer in queryset.filter(pk__in=selected_ids):
            customer.restore()
            restored_count += 1

        messages.success(request, f"Clientes restaurados: {restored_count}.")
        return redirect("customer-deleted-list")


class CustomerRestoreAllView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.change_customer"

    def post(self, request):
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=True)
        query = request.POST.get("q")
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
                | Q(node__name__icontains=query)
            )

        restored_count = 0
        for customer in queryset:
            customer.restore()
            restored_count += 1

        messages.success(request, f"Clientes restaurados desde eliminados: {restored_count}.")
        return redirect("customer-deleted-list")


class CustomerPermanentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.delete_customer"

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, company=self.get_company(), is_deleted=True)
        try:
            customer.delete()
            messages.success(request, "Cliente eliminado definitivamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar definitivamente porque el cliente tiene historial relacionado protegido.")
        return redirect("customer-deleted-list")


class CustomerPortalAccountToggleView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.change_customer"

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, company=self.get_company(), is_deleted=False)
        account = getattr(customer, "portal_account", None)
        if not account:
            messages.warning(request, "Este cliente todavia no tiene una cuenta portal creada.")
            return redirect("customer-detail", pk=customer.pk)
        account.is_active = not account.is_active
        account.save(update_fields=["is_active", "updated_at"])
        if account.is_active:
            messages.success(request, "La cuenta portal fue activada nuevamente.")
        else:
            messages.success(request, "La cuenta portal fue bloqueada correctamente.")
        return redirect("customer-detail", pk=customer.pk)


class CustomerBulkPermanentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, CompanyMixin, View):
    permission_required = "customers.delete_customer"

    def post(self, request):
        selected_ids = request.POST.getlist("customer_ids")
        queryset = Customer.objects.filter(company=self.get_company(), is_deleted=True)
        if not selected_ids:
            messages.warning(request, "Selecciona al menos un cliente para eliminar definitivamente.")
            return redirect("customer-deleted-list")

        deleted_count = 0
        blocked_count = 0
        for customer in queryset.filter(pk__in=selected_ids):
            try:
                customer.delete()
                deleted_count += 1
            except ProtectedError:
                blocked_count += 1

        if deleted_count:
            messages.success(request, f"Clientes eliminados definitivamente: {deleted_count}.")
        if blocked_count:
            messages.warning(request, f"Clientes no eliminados por historial protegido: {blocked_count}.")
        return redirect("customer-deleted-list")
