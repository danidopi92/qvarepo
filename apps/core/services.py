from django.db import transaction
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model

from apps.billing.models import Invoice, InvoiceItem, Payment, SuspensionEvent
from apps.client_portal.models import CustomerPortalAccount
from apps.core.models import AuditLog
from apps.customers.models import Customer, CustomerContact, CustomerDocument, CustomerNote, Node
from apps.integrations.models import IntegrationEvent
from apps.services_app.models import CustomerService, Equipment, ServicePlan


ROLE_MAP = {
    "Administrador": [],
    "Facturacion": [
        "add_invoice", "change_invoice", "view_invoice",
        "add_payment", "change_payment", "view_payment",
    ],
    "Tecnico": [
        "view_customerservice", "change_customerservice",
        "view_suspensionevent", "add_suspensionevent",
    ],
    "Supervisor": [
        "view_invoice", "view_payment", "view_customer", "view_integrationevent",
    ],
    "Solo lectura": [
        "view_customer", "view_customerservice", "view_invoice", "view_payment",
    ],
}


def bootstrap_roles():
    for group_name, permission_codes in ROLE_MAP.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        if group_name == "Administrador":
            group.permissions.set(Permission.objects.all())
        else:
            group.permissions.set(Permission.objects.filter(codename__in=permission_codes))


def log_action(*, company, actor, model_name, object_id, action, changes=None, request_id="", ip_address=None):
    AuditLog.objects.create(
        company=company,
        actor=actor,
        model_name=model_name,
        object_id=str(object_id),
        action=action,
        changes=changes or {},
        request_id=request_id,
        ip_address=ip_address,
    )


def build_setup_wizard(company):
    User = get_user_model()
    nodes_count = Node.objects.filter(company=company, is_deleted=False).count() if company else 0
    plans_count = ServicePlan.objects.filter(company=company, is_deleted=False).count() if company else 0
    customers_count = Customer.objects.filter(company=company, is_deleted=False).count() if company else 0
    services_count = CustomerService.objects.filter(company=company, is_deleted=False).count() if company else 0
    invoices_count = Invoice.objects.filter(company=company, is_deleted=False).count() if company else 0
    users_count = User.objects.filter(is_active=True).count()
    active_admin_count = User.objects.filter(is_active=True, is_superuser=True).count()
    active_staff_count = User.objects.filter(is_active=True, is_superuser=False).count()
    has_company_profile = bool(
        company and any([company.legal_name, company.tax_id, company.email, company.phone, company.address, company.logo])
    )

    steps = [
        {
            "slug": "company",
            "title": "Configura tu empresa",
            "description": "Ajusta branding, datos comerciales y secuencia de facturacion.",
            "done": has_company_profile,
            "required": True,
            "primary_url_name": "settings-branding",
            "primary_label": "Configurar empresa",
        },
        {
            "slug": "admin",
            "title": "Crea el administrador inicial",
            "description": "Define la cuenta principal que luego usara el panel administrativo.",
            "done": active_admin_count > 0,
            "required": True,
            "primary_url_name": "setup-wizard-step",
            "primary_label": "Crear administrador",
            "meta": {"count": active_admin_count},
        },
        {
            "slug": "users",
            "title": "Usuarios y roles",
            "description": "Crea al menos un usuario operativo adicional y asignale su rol.",
            "done": active_staff_count > 0,
            "required": True,
            "primary_url_name": "settings-users",
            "primary_label": "Gestionar usuarios",
            "meta": {"count": users_count, "active_staff_count": active_staff_count},
        },
        {
            "slug": "nodes",
            "title": "Carga nodos",
            "description": "Crea nodos manualmente o importalos desde plantilla.",
            "done": nodes_count > 0,
            "required": True,
            "primary_url_name": "settings-nodes",
            "primary_label": "Gestionar nodos",
            "secondary_url_name": "settings-nodes",
            "secondary_label": "Importar nodos",
            "meta": {"count": nodes_count},
        },
        {
            "slug": "plans",
            "title": "Crea planes",
            "description": "Define los planes que usaras luego en clientes y servicios.",
            "done": plans_count > 0,
            "required": True,
            "primary_url_name": "settings-service-plans",
            "primary_label": "Gestionar planes",
            "meta": {"count": plans_count},
        },
        {
            "slug": "customers",
            "title": "Carga clientes",
            "description": "Importa tus clientes o déjalo para después si todavía no estás listo.",
            "done": customers_count > 0,
            "required": False,
            "primary_url_name": "customer-import",
            "primary_label": "Importar clientes",
            "secondary_url_name": "customer-create",
            "secondary_label": "Nuevo cliente",
            "meta": {"count": customers_count},
        },
        {
            "slug": "services",
            "title": "Asigna servicios",
            "description": "Relaciona a cada cliente con su plan y condiciones de servicio.",
            "done": services_count > 0,
            "required": False,
            "primary_url_name": "service-create",
            "primary_label": "Asignar servicio",
            "meta": {"count": services_count},
        },
        {
            "slug": "billing",
            "title": "Empieza a facturar",
            "description": "Genera la primera factura o lanza tu facturacion mensual.",
            "done": invoices_count > 0,
            "required": False,
            "primary_url_name": "invoice-create",
            "primary_label": "Crear factura",
            "secondary_url_name": "invoice-generate-monthly",
            "secondary_label": "Facturacion mensual",
            "meta": {"count": invoices_count},
        },
    ]

    required_steps = [step for step in steps if step["required"]]
    completed_required = sum(1 for step in required_steps if step["done"])
    progress = int((completed_required / len(required_steps)) * 100) if required_steps else 0
    next_step = next((step["slug"] for step in steps if not step["done"]), "finish")
    return {
        "steps": steps,
        "steps_by_slug": {step["slug"]: step for step in steps},
        "completed": completed_required,
        "total": len(required_steps),
        "progress": progress,
        "required_total": len(required_steps),
        "ready_for_dashboard": completed_required == len(required_steps),
        "next_step_slug": next_step,
        "is_needed": completed_required < len(required_steps),
    }


@transaction.atomic
def reset_company_operational_data(company, actor=None):
    User = get_user_model()
    counts = {}

    counts["integration_events"] = IntegrationEvent.objects.filter(company=company).count()
    IntegrationEvent.objects.filter(company=company).delete()

    counts["suspension_events"] = SuspensionEvent.objects.filter(company=company).count()
    SuspensionEvent.objects.filter(company=company).delete()

    counts["payments"] = Payment.objects.filter(company=company).count()
    Payment.objects.filter(company=company).delete()

    counts["invoice_items"] = InvoiceItem.objects.filter(company=company).count()
    InvoiceItem.objects.filter(company=company).delete()

    counts["invoices"] = Invoice.objects.filter(company=company).count()
    Invoice.objects.filter(company=company).delete()

    counts["portal_accounts"] = CustomerPortalAccount.objects.filter(customer__company=company).count()
    CustomerPortalAccount.objects.filter(customer__company=company).delete()

    counts["customer_documents"] = CustomerDocument.objects.filter(company=company).count()
    CustomerDocument.objects.filter(company=company).delete()

    counts["customer_contacts"] = CustomerContact.objects.filter(company=company).count()
    CustomerContact.objects.filter(company=company).delete()

    counts["customer_notes"] = CustomerNote.objects.filter(company=company).count()
    CustomerNote.objects.filter(company=company).delete()

    counts["customer_services"] = CustomerService.objects.filter(company=company).count()
    CustomerService.objects.filter(company=company).delete()

    counts["customers"] = Customer.objects.filter(company=company).count()
    Customer.objects.filter(company=company).delete()

    counts["equipment"] = Equipment.objects.filter(company=company).count()
    Equipment.objects.filter(company=company).delete()

    counts["nodes"] = Node.objects.filter(company=company).count()
    Node.objects.filter(company=company).delete()

    counts["plans"] = ServicePlan.objects.filter(company=company).count()
    ServicePlan.objects.filter(company=company).delete()

    counts["audit_logs"] = AuditLog.objects.filter(company=company).count()
    AuditLog.objects.filter(company=company).delete()

    if hasattr(company, "systemsetting"):
        company.systemsetting.invoice_sequence = 1
        company.systemsetting.save(update_fields=["invoice_sequence", "updated_at"])

    company.legal_name = ""
    company.tax_id = ""
    company.email = ""
    company.phone = ""
    company.address = ""
    company.logo = None
    company.save(update_fields=["legal_name", "tax_id", "email", "phone", "address", "logo", "updated_at"])

    counts["users"] = User.objects.count()
    User.objects.all().delete()

    log_action(
        company=company,
        actor=None,
        model_name="Company",
        object_id=company.pk,
        action="reset_operational_data",
        changes=counts,
    )
    return counts
