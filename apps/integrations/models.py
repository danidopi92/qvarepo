from django.db import models

from apps.core.models import CompanyScopedModel
from apps.customers.models import Customer


class IntegrationEvent(CompanyScopedModel):
    class Provider(models.TextChoices):
        OPENCLAW = "openclaw", "OpenClaw"

    class Direction(models.TextChoices):
        OUTBOUND = "outbound", "Saliente"
        INBOUND = "inbound", "Entrante"

    provider = models.CharField(max_length=30, choices=Provider.choices, default=Provider.OPENCLAW)
    direction = models.CharField(max_length=20, choices=Direction.choices, default=Direction.OUTBOUND)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="integration_events")
    action = models.CharField(max_length=100, db_index=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    external_reference = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at"]
