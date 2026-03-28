from rest_framework import decorators, permissions, response, status, viewsets

from apps.billing.models import Invoice, Payment, SuspensionEvent
from apps.billing.serializers import InvoiceSerializer, PaymentSerializer, SuspensionEventSerializer
from apps.billing.services import reactivate_customer, suspend_customer_for_nonpayment
from apps.core.models import Company


class CompanyQuerySetMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class InvoiceViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["invoice_number", "customer__full_name"]
    filterset_fields = ["status", "customer", "issue_date", "due_date"]

    def get_queryset(self):
        return Invoice.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "currency")

    def perform_create(self, serializer):
        serializer.save(
            company=self.get_company(),
            invoice_number=Invoice.next_invoice_number(self.get_company()),
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class PaymentViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["customer", "invoice", "method", "currency"]
    search_fields = ["reference", "customer__full_name"]

    def get_queryset(self):
        return Payment.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "invoice", "currency")

    def perform_create(self, serializer):
        payment = serializer.save(
            company=self.get_company(),
            registered_by=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        payment.apply()


class SuspensionEventViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = SuspensionEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["customer", "action", "technical_executed"]

    def get_queryset(self):
        return SuspensionEvent.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "service")

    @decorators.action(detail=True, methods=["post"])
    def execute_suspend(self, request, pk=None):
        event = self.get_object()
        result = suspend_customer_for_nonpayment(event.customer, request.user, event.reason)
        return response.Response({"event_id": result.pk}, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def execute_reactivate(self, request, pk=None):
        event = self.get_object()
        result = reactivate_customer(event.customer, request.user, event.reason)
        return response.Response({"event_id": result.pk}, status=status.HTTP_200_OK)
