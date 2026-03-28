from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel
from apps.customers.models import Customer, Node


class Equipment(CompanyScopedModel):
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=120, blank=True)
    mac_address = models.CharField(max_length=50, blank=True, db_index=True)
    equipment_type = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ServicePlan(CompanyScopedModel):
    class ServiceType(models.TextChoices):
        INTERNET = "internet", "Internet"
        VOIP = "voip", "VoIP"
        IPTV = "iptv", "IPTV"
        OTHER = "other", "Otro"

    name = models.CharField(max_length=255)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, default=ServiceType.INTERNET)
    speed_label = models.CharField(max_length=120, blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "name")]

    def __str__(self):
        return self.name


class CustomerService(CompanyScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        SUSPENDED = "suspended", "Suspendido"
        PENDING = "pending", "Pendiente"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="services")
    plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, related_name="customer_services")
    service_type = models.CharField(max_length=20, choices=ServicePlan.ServiceType.choices, default=ServicePlan.ServiceType.INTERNET)
    speed_label = models.CharField(max_length=120, blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateField()
    cut_off_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    equipment = models.ForeignKey(Equipment, null=True, blank=True, on_delete=models.SET_NULL)
    router_cpe = models.CharField(max_length=255, blank=True)
    mac_address = models.CharField(max_length=50, blank=True, db_index=True)
    technical_reference = models.CharField(max_length=255, blank=True)
    pppoe_username = models.CharField(max_length=120, blank=True)
    node = models.ForeignKey(Node, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["customer__full_name", "plan__name"]

    def __str__(self):
        return f"{self.customer} - {self.plan}"
