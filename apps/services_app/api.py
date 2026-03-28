from rest_framework import permissions, viewsets

from apps.core.models import Company
from apps.services_app.models import CustomerService, ServicePlan
from apps.services_app.serializers import CustomerServiceSerializer, ServicePlanSerializer


class CompanyQuerySetMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class ServicePlanViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = ServicePlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "service_type"]

    def get_queryset(self):
        return ServicePlan.objects.filter(company=self.get_company(), is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(company=self.get_company(), created_by=self.request.user, updated_by=self.request.user)


class CustomerServiceViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = CustomerServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["customer__full_name", "plan__name", "pppoe_username", "mac_address"]
    filterset_fields = ["status", "node", "service_type"]

    def get_queryset(self):
        return CustomerService.objects.filter(company=self.get_company(), is_deleted=False).select_related("customer", "plan", "node")

    def perform_create(self, serializer):
        serializer.save(company=self.get_company(), created_by=self.request.user, updated_by=self.request.user)
