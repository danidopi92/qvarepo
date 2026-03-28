from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin

from apps.billing.models import Invoice, Payment, SuspensionEvent
from apps.core.models import Company
from apps.core.forms import AdminBootstrapForm, CompanyBrandingForm, ResetPlatformForm, SystemSettingForm, UserRoleForm, UserUpdateForm
from apps.core.models import SystemSetting
from apps.core.services import bootstrap_roles, build_setup_wizard, reset_company_operational_data
from apps.customers.forms import ImportCustomersForm, NodeForm
from apps.customers.models import Customer, Node
from apps.customers.services import import_customers, import_nodes
from apps.integrations.models import IntegrationEvent
from apps.services_app.forms import ServicePlanForm
from apps.services_app.models import CustomerService, ServicePlan


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_company(self):
        return Company.objects.filter(is_active=True).first()

    def dispatch(self, request, *args, **kwargs):
        company = self.get_company()
        setup_wizard = build_setup_wizard(company)
        if setup_wizard["is_needed"]:
            messages.info(request, "Completa primero el wizard inicial antes de entrar al dashboard.")
            return redirect("setup-wizard")
        if not request.user.is_authenticated:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        company = self.get_company()
        invoices = Invoice.objects.filter(company=company, is_deleted=False)
        payments_today = Payment.objects.filter(company=company, paid_at__date=now.date(), is_deleted=False)
        context.update(
            {
                "metrics": {
                    "customers_total": Customer.objects.filter(company=company, is_deleted=False).count(),
                    "customers_active": Customer.objects.filter(company=company, status=Customer.Status.ACTIVE, is_deleted=False).count(),
                    "customers_suspended": Customer.objects.filter(company=company, status=Customer.Status.SUSPENDED, is_deleted=False).count(),
                    "invoices_issued": invoices.exclude(status=Invoice.Status.DRAFT).count(),
                    "invoices_overdue": invoices.filter(status=Invoice.Status.OVERDUE).count(),
                    "payments_today": payments_today.count(),
                    "income_month": Payment.objects.filter(
                        company=company, paid_at__year=now.year, paid_at__month=now.month, is_deleted=False
                    ).aggregate(total=Sum("amount"))["total"] or 0,
                    "pending_debt": invoices.aggregate(total=Sum("balance_due"))["total"] or 0,
                },
                "alerts": Invoice.objects.filter(company=company, status=Invoice.Status.OVERDUE, is_deleted=False).select_related("customer")[:5],
                "upcoming_due": invoices.filter(
                    due_date__gte=now.date(),
                    due_date__lte=now.date() + timezone.timedelta(days=7),
                ).select_related("customer")[:10],
                "suspensions": SuspensionEvent.objects.filter(company=company, is_deleted=False).select_related("customer").order_by("-created_at")[:5],
                "recent_payments": Payment.objects.filter(company=company, is_deleted=False).select_related("customer", "invoice").order_by("-paid_at")[:6],
                "setup_wizard": build_setup_wizard(company),
            }
        )
        return context


class SettingsCompanyMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()

    def get_system_setting(self):
        return SystemSetting.load()


class SettingsHomeView(LoginRequiredMixin, SettingsCompanyMixin, TemplateView):
    template_name = "settings/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context["summary"] = {
            "users": User.objects.count(),
            "roles": Group.objects.count(),
            "nodes": Node.objects.filter(company=self.get_company(), is_deleted=False).count(),
            "plans": ServicePlan.objects.filter(company=self.get_company()).count(),
            "reports": 3,
            "openclaw_events": IntegrationEvent.objects.count(),
        }
        context["setup_wizard"] = build_setup_wizard(self.get_company())
        return context


class BrandingSettingsView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "core.change_systemsetting"
    template_name = "settings/branding.html"

    def get(self, request):
        company = self.get_company()
        system_setting = self.get_system_setting()
        return render(
            request,
            self.template_name,
            {
                "company_form": CompanyBrandingForm(instance=company),
                "system_form": SystemSettingForm(instance=system_setting),
            },
        )

    def post(self, request):
        company = self.get_company()
        system_setting = self.get_system_setting()
        company_form = CompanyBrandingForm(request.POST, request.FILES, instance=company)
        system_form = SystemSettingForm(request.POST, instance=system_setting)
        if company_form.is_valid() and system_form.is_valid():
            company_form.save()
            system_form.save()
            messages.success(request, "Ajustes de branding actualizados.")
            return redirect("settings-branding")
        return render(request, self.template_name, {"company_form": company_form, "system_form": system_form})


class UserManagementView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "auth.view_user"
    template_name = "settings/users.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        User = get_user_model()
        query = self.request.GET.get("q")
        queryset = User.objects.prefetch_related("groups").order_by("username")
        if query:
            queryset = queryset.filter(username__icontains=query)
        return queryset


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.add_user"
    template_name = "settings/user_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": UserRoleForm(), "mode": "create"})

    def post(self, request):
        form = UserRoleForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.groups.set(form.cleaned_data["groups"])
            messages.success(request, "Usuario creado correctamente.")
            return redirect("settings-users")
        return render(request, self.template_name, {"form": form, "mode": "create"})


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.change_user"
    template_name = "settings/user_form.html"

    def get_object(self, pk):
        User = get_user_model()
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        user = self.get_object(pk)
        return render(request, self.template_name, {"form": UserUpdateForm(instance=user), "mode": "update", "target_user": user})

    def post(self, request, pk):
        user = self.get_object(pk)
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            user.groups.set(form.cleaned_data["groups"])
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("settings-users")
        return render(request, self.template_name, {"form": form, "mode": "update", "target_user": user})


class ReportsSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "settings/reports.html"


class OpenClawSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "settings/openclaw.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["openclaw"] = {
            "base_url": settings.OPENCLAW_BASE_URL,
            "timeout": settings.OPENCLAW_TIMEOUT,
            "simulation_mode": settings.OPENCLAW_SIMULATION_MODE,
            "retry_attempts": settings.OPENCLAW_RETRY_ATTEMPTS,
            "api_key_masked": f"{settings.OPENCLAW_API_KEY[:4]}..." if settings.OPENCLAW_API_KEY else "",
        }
        context["recent_events"] = IntegrationEvent.objects.select_related("customer").order_by("-created_at")[:10]
        return context


class SetupWizardView(SettingsCompanyMixin, TemplateView):
    template_name = "settings/setup_wizard.html"
    step_order = ["welcome", "company", "admin", "users", "nodes", "plans", "customers", "services", "billing", "finish"]

    def get_current_step(self):
        step = self.kwargs.get("step", "welcome")
        return step if step in self.step_order else "welcome"

    def get_wizard(self):
        return build_setup_wizard(self.get_company())

    def get_next_step(self, current_step, wizard):
        if current_step == "welcome":
            return "company"
        if current_step == "finish":
            return "finish"
        if wizard["ready_for_dashboard"] and current_step in {"company", "admin", "users", "nodes", "plans", "customers"}:
            return "finish"
        try:
            current_index = self.step_order.index(current_step)
        except ValueError:
            return "company"
        for next_step in self.step_order[current_index + 1:]:
            if next_step == "finish":
                return "finish"
            wizard_step = next((item for item in wizard["steps"] if item["slug"] == next_step), None)
            if wizard_step and (wizard_step["required"] or not wizard_step["done"]):
                return next_step
        return "finish"

    def get_previous_step(self, current_step):
        try:
            current_index = self.step_order.index(current_step)
        except ValueError:
            return None
        if current_index == 0:
            return None
        return self.step_order[current_index - 1]

    def get_step_navigation(self, wizard, current_step):
        navigation = [
            {
                "slug": "welcome",
                "title": "Inicio",
                "done": False,
                "current": current_step == "welcome",
            }
        ]
        for step in wizard["steps"]:
            navigation.append(
                {
                    "slug": step["slug"],
                    "title": step["title"],
                    "done": step["done"],
                    "required": step["required"],
                    "current": current_step == step["slug"],
                }
            )
        navigation.append(
            {
                "slug": "finish",
                "title": "Finalizar",
                "done": wizard["ready_for_dashboard"],
                "current": current_step == "finish",
            }
        )
        return navigation

    def get_company_instance(self):
        company = self.get_company()
        if company:
            return company
        return Company.objects.create(name="Nueva empresa")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wizard = self.get_wizard()
        current_step = self.get_current_step()
        if current_step == "finish" and not wizard["ready_for_dashboard"]:
            current_step = wizard["next_step_slug"]
        company = self.get_company_instance()
        system_setting = self.get_system_setting()
        bootstrap_roles()
        context.update(
            {
                "setup_wizard": wizard,
                "wizard_step": current_step,
                "wizard_navigation": self.get_step_navigation(wizard, current_step),
                "wizard_previous_step": self.get_previous_step(current_step),
                "wizard_next_step": self.get_next_step(current_step, wizard),
                "company_form": kwargs.get("company_form") or CompanyBrandingForm(instance=company),
                "system_form": kwargs.get("system_form") or SystemSettingForm(instance=system_setting),
                "admin_form": kwargs.get("admin_form") or AdminBootstrapForm(),
                "user_form": kwargs.get("user_form") or UserRoleForm(),
                "users_list": get_user_model().objects.order_by("username")[:8],
                "node_form": kwargs.get("node_form") or NodeForm(),
                "nodes_list": Node.objects.filter(company=company, is_deleted=False).order_by("name")[:8],
                "plan_form": kwargs.get("plan_form") or ServicePlanForm(),
                "plans_list": ServicePlan.objects.filter(company=company, is_deleted=False).order_by("name")[:8],
                "customer_import_form": kwargs.get("customer_import_form") or ImportCustomersForm(),
                "customers_list": Customer.objects.filter(company=company, is_deleted=False).order_by("full_name")[:8],
                "services_list": CustomerService.objects.filter(company=company, is_deleted=False).select_related("customer", "plan")[:8],
                "invoices_list": Invoice.objects.filter(company=company, is_deleted=False).select_related("customer")[:8],
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        wizard = self.get_wizard()
        if self.get_current_step() == "welcome" and wizard["ready_for_dashboard"]:
            return redirect("setup-wizard-step", step="finish")
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        current_step = self.get_current_step()
        company = self.get_company_instance()
        system_setting = self.get_system_setting()
        bootstrap_roles()

        if current_step == "company":
            company_form = CompanyBrandingForm(request.POST, request.FILES, instance=company)
            system_form = SystemSettingForm(request.POST, instance=system_setting)
            if company_form.is_valid() and system_form.is_valid():
                company_form.save()
                system_form.save()
                messages.success(request, "Empresa configurada correctamente.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(company_form=company_form, system_form=system_form))

        if current_step == "admin":
            admin_form = AdminBootstrapForm(request.POST)
            if admin_form.is_valid():
                admin_form.save()
                messages.success(request, "Administrador inicial creado correctamente.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(admin_form=admin_form))

        if current_step == "users":
            user_form = UserRoleForm(request.POST)
            if user_form.is_valid():
                user = user_form.save()
                user.groups.set(user_form.cleaned_data["groups"])
                messages.success(request, "Usuario creado correctamente.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(user_form=user_form))

        if current_step == "nodes":
            if request.FILES.get("file"):
                import_form = ImportCustomersForm(request.POST, request.FILES)
                if import_form.is_valid():
                    result = import_nodes(
                        company,
                        import_form.cleaned_data["file"],
                        user=request.user if request.user.is_authenticated else None,
                    )
                    messages.success(request, f"Nodos importados. Creados: {result['created']} | Actualizados: {result['updated']} | Omitidos: {result['skipped']}.")
                    return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
                return self.render_to_response(self.get_context_data(customer_import_form=import_form))
            node_form = NodeForm(request.POST)
            if node_form.is_valid():
                node = node_form.save(commit=False)
                node.company = company
                node.created_by = request.user if request.user.is_authenticated else None
                node.updated_by = request.user if request.user.is_authenticated else None
                node.save()
                messages.success(request, "Nodo creado correctamente.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(node_form=node_form))

        if current_step == "plans":
            plan_form = ServicePlanForm(request.POST)
            if plan_form.is_valid():
                plan = plan_form.save(commit=False)
                plan.company = company
                actor = request.user if request.user.is_authenticated else None
                plan.created_by = actor
                plan.updated_by = actor
                plan.save()
                messages.success(request, "Plan creado correctamente.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(plan_form=plan_form))

        if current_step == "customers":
            import_form = ImportCustomersForm(request.POST, request.FILES)
            if import_form.is_valid():
                result = import_customers(
                    company,
                    import_form.cleaned_data["file"],
                    user=request.user if request.user.is_authenticated else None,
                )
                messages.success(request, f"Clientes importados. Creados: {result['created']} | Actualizados: {result['updated']} | Omitidos: {result['skipped']}.")
                return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))
            return self.render_to_response(self.get_context_data(customer_import_form=import_form))

        messages.info(request, "Continua con el siguiente paso del wizard.")
        return redirect("setup-wizard-step", step=self.get_next_step(current_step, self.get_wizard()))

class ResetPlatformView(LoginRequiredMixin, UserPassesTestMixin, SettingsCompanyMixin, View):
    template_name = "settings/reset.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        return render(request, self.template_name, {"form": ResetPlatformForm()})

    def post(self, request):
        form = ResetPlatformForm(request.POST)
        if form.is_valid():
            counts = reset_company_operational_data(self.get_company(), actor=request.user)
            logout(request)
            messages.success(request, "Reset total completado. La operacion fue limpiada y la configuracion base se mantuvo.")
            messages.info(request, f"Resumen: clientes {counts['customers']}, nodos {counts['nodes']}, planes {counts['plans']}, servicios {counts['customer_services']}, facturas {counts['invoices']}, pagos {counts['payments']}.")
            messages.warning(request, "Ahora completa el wizard inicial para volver a dejar la plataforma operativa.")
            return redirect("setup-wizard")
        return render(request, self.template_name, {"form": form})


class NodeSettingsView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, ListView):
    permission_required = "customers.view_node"
    template_name = "settings/nodes.html"
    context_object_name = "nodes"

    def get_queryset(self):
        company = self.get_company()
        queryset = Node.objects.filter(company=company, is_deleted=False).order_by("name")
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["import_form"] = ImportCustomersForm()
        return context


class NodeCreateView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "customers.add_node"
    template_name = "settings/node_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": NodeForm(), "mode": "create"})

    def post(self, request):
        form = NodeForm(request.POST)
        if form.is_valid():
            node = form.save(commit=False)
            node.company = self.get_company()
            node.created_by = request.user
            node.updated_by = request.user
            node.save()
            messages.success(request, "Nodo creado correctamente.")
            return redirect("settings-nodes")
        return render(request, self.template_name, {"form": form, "mode": "create"})


class NodeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "customers.change_node"
    template_name = "settings/node_form.html"

    def get_object(self, pk):
        return get_object_or_404(Node, pk=pk, company=self.get_company(), is_deleted=False)

    def get(self, request, pk):
        node = self.get_object(pk)
        return render(request, self.template_name, {"form": NodeForm(instance=node), "mode": "update", "node": node})

    def post(self, request, pk):
        node = self.get_object(pk)
        form = NodeForm(request.POST, instance=node)
        if form.is_valid():
            edited_node = form.save(commit=False)
            edited_node.updated_by = request.user
            edited_node.save()
            messages.success(request, "Nodo actualizado correctamente.")
            return redirect("settings-nodes")
        return render(request, self.template_name, {"form": form, "mode": "update", "node": node})


class NodeImportView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "customers.add_node"

    def post(self, request):
        form = ImportCustomersForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Selecciona un archivo CSV o Excel valido.")
            return redirect("settings-nodes")

        results = import_nodes(self.get_company(), form.cleaned_data["file"], request.user)
        messages.success(
            request,
            f"Importacion de nodos completada. Creados: {results['created']} | Actualizados: {results['updated']} | Omitidos: {results['skipped']}.",
        )
        for error in results["errors"][:10]:
            messages.warning(request, error)
        return redirect("settings-nodes")


class NodeBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "customers.delete_node"

    def post(self, request):
        selected_ids = request.POST.getlist("node_ids")
        if not selected_ids:
            messages.warning(request, "Selecciona al menos un nodo para eliminar.")
            return redirect("settings-nodes")

        queryset = Node.objects.filter(company=self.get_company(), is_deleted=False, pk__in=selected_ids)
        deleted_count = 0
        for node in queryset:
            node.soft_delete(request.user)
            deleted_count += 1

        messages.success(request, f"Nodos enviados a baja logica: {deleted_count}.")
        return redirect("settings-nodes")


class NodeBulkDeleteFilteredView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "customers.delete_node"

    def post(self, request):
        queryset = Node.objects.filter(company=self.get_company(), is_deleted=False)
        query = request.POST.get("q")
        if query:
            queryset = queryset.filter(name__icontains=query)

        deleted_count = 0
        for node in queryset:
            node.soft_delete(request.user)
            deleted_count += 1

        messages.success(request, f"Nodos filtrados enviados a baja logica: {deleted_count}.")
        return redirect("settings-nodes")


class ServicePlanSettingsView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, ListView):
    permission_required = "services_app.view_serviceplan"
    template_name = "settings/plans.html"
    context_object_name = "plans"

    def get_queryset(self):
        company = self.get_company()
        queryset = ServicePlan.objects.filter(company=company).order_by("service_type", "name")
        query = self.request.GET.get("q")
        service_type = self.request.GET.get("service_type")
        if query:
            queryset = queryset.filter(name__icontains=query)
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_type_choices"] = ServicePlan.ServiceType.choices
        return context


class ServicePlanCreateView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "services_app.add_serviceplan"
    template_name = "settings/plan_form.html"

    def get(self, request):
        initial_type = request.GET.get("service_type", ServicePlan.ServiceType.INTERNET)
        form = ServicePlanForm(initial={"service_type": initial_type})
        return render(request, self.template_name, {"form": form, "mode": "create"})

    def post(self, request):
        form = ServicePlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.company = self.get_company()
            plan.save()
            messages.success(request, "Plan creado correctamente.")
            return redirect("settings-service-plans")
        return render(request, self.template_name, {"form": form, "mode": "create"})


class ServicePlanUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SettingsCompanyMixin, View):
    permission_required = "services_app.change_serviceplan"
    template_name = "settings/plan_form.html"

    def get_object(self, pk):
        return get_object_or_404(ServicePlan, pk=pk, company=self.get_company())

    def get(self, request, pk):
        plan = self.get_object(pk)
        form = ServicePlanForm(instance=plan)
        return render(request, self.template_name, {"form": form, "mode": "update", "plan": plan})

    def post(self, request, pk):
        plan = self.get_object(pk)
        form = ServicePlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Plan actualizado correctamente.")
            return redirect("settings-service-plans")
        return render(request, self.template_name, {"form": form, "mode": "update", "plan": plan})
