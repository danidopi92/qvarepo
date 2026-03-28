from rest_framework import decorators, permissions, response, status, viewsets

from apps.core.models import Company
from apps.customers.models import Customer
from apps.integrations.models import IntegrationEvent
from apps.integrations.serializers import IntegrationEventSerializer, OpenClawActionSerializer
from apps.integrations.services import OpenClawGateway


class CompanyQuerySetMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class IntegrationEventViewSet(CompanyQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = IntegrationEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["action", "customer__full_name", "external_reference"]
    filterset_fields = ["action", "success", "provider"]

    def get_queryset(self):
        return IntegrationEvent.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer")


class OpenClawActionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=["post"], url_path="suspend-customer")
    def suspend_customer(self, request):
        serializer = OpenClawActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = Customer.objects.get(pk=serializer.validated_data["customer_id"])
        result = OpenClawGateway().suspend_customer(customer)
        return response.Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_502_BAD_GATEWAY)

    @decorators.action(detail=False, methods=["post"], url_path="reactivate-customer")
    def reactivate_customer(self, request):
        serializer = OpenClawActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = Customer.objects.get(pk=serializer.validated_data["customer_id"])
        result = OpenClawGateway().reactivate_customer(customer)
        return response.Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_502_BAD_GATEWAY)

    @decorators.action(detail=False, methods=["post"], url_path="check-customer-status")
    def check_customer_status(self, request):
        serializer = OpenClawActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = Customer.objects.get(pk=serializer.validated_data["customer_id"])
        result = OpenClawGateway().check_customer_status(customer)
        return response.Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_502_BAD_GATEWAY)

    @decorators.action(detail=False, methods=["post"], url_path="run-action")
    def run_action(self, request):
        serializer = OpenClawActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = None
        if serializer.validated_data.get("customer_id"):
            customer = Customer.objects.get(pk=serializer.validated_data["customer_id"])
        result = OpenClawGateway().run_action(customer, serializer.validated_data.get("command", ""), serializer.validated_data.get("payload"))
        return response.Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_502_BAD_GATEWAY)
