import logging
import time

import requests
from django.conf import settings

from apps.core.models import Company
from apps.integrations.models import IntegrationEvent

logger = logging.getLogger(__name__)


class OpenClawGateway:
    def __init__(self):
        self.base_url = settings.OPENCLAW_BASE_URL.rstrip("/")
        self.api_key = settings.OPENCLAW_API_KEY
        self.timeout = settings.OPENCLAW_TIMEOUT
        self.simulation_mode = settings.OPENCLAW_SIMULATION_MODE
        self.retry_attempts = settings.OPENCLAW_RETRY_ATTEMPTS
        self.company = Company.objects.filter(is_active=True).first()

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _log_event(self, *, customer=None, action="", request_payload=None, response_payload=None, status_code=None, success=False, error_message="", retry_count=0, duration_ms=0, external_reference=""):
        return IntegrationEvent.objects.create(
            company=self.company,
            customer=customer,
            action=action,
            request_payload=request_payload or {},
            response_payload=response_payload or {},
            status_code=status_code,
            success=success,
            error_message=error_message,
            retry_count=retry_count,
            duration_ms=duration_ms,
            external_reference=external_reference,
        )

    def _simulate(self, customer, action, payload):
        response = {
            "success": True,
            "reference": f"mock-{action}-{customer.pk if customer else 'na'}",
            "summary": f"Simulacion OpenClaw para {action}",
            "payload": payload,
        }
        self._log_event(
            customer=customer,
            action=action,
            request_payload=payload,
            response_payload=response,
            status_code=200,
            success=True,
            external_reference=response["reference"],
        )
        return response

    def _request(self, endpoint, payload, customer=None, action="run-action"):
        if self.simulation_mode:
            return self._simulate(customer, action, payload)

        last_error = ""
        for attempt in range(1, self.retry_attempts + 1):
            started = time.perf_counter()
            try:
                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                res = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
                duration = int((time.perf_counter() - started) * 1000)
                response_data = res.json() if res.content else {}
                event = self._log_event(
                    customer=customer,
                    action=action,
                    request_payload=payload,
                    response_payload=response_data,
                    status_code=res.status_code,
                    success=res.ok,
                    retry_count=attempt - 1,
                    duration_ms=duration,
                    external_reference=response_data.get("reference", ""),
                )
                response_data["event_id"] = event.pk
                if res.ok:
                    return response_data
                last_error = response_data.get("detail", f"HTTP {res.status_code}")
            except requests.RequestException as exc:
                duration = int((time.perf_counter() - started) * 1000)
                last_error = str(exc)
                self._log_event(
                    customer=customer,
                    action=action,
                    request_payload=payload,
                    response_payload={},
                    success=False,
                    error_message=last_error,
                    retry_count=attempt,
                    duration_ms=duration,
                )
                logger.exception("OpenClaw request failed")
        return {"success": False, "summary": last_error, "reference": ""}

    def suspend_customer(self, customer):
        return self._request(
            "suspend-customer/",
            {"customer_id": customer.pk, "name": customer.full_name, "ip_address": customer.assigned_ip},
            customer,
            "suspend-customer",
        )

    def reactivate_customer(self, customer):
        return self._request(
            "reactivate-customer/",
            {"customer_id": customer.pk, "name": customer.full_name, "ip_address": customer.assigned_ip},
            customer,
            "reactivate-customer",
        )

    def check_customer_status(self, customer):
        return self._request(
            "check-customer-status/",
            {"customer_id": customer.pk, "ip_address": customer.assigned_ip},
            customer,
            "check-customer-status",
        )

    def run_action(self, customer, command, payload=None):
        data = {"customer_id": customer.pk if customer else None, "command": command, "payload": payload or {}}
        return self._request("run-action/", data, customer, "run-action")
