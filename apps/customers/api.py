from rest_framework import permissions, viewsets

from apps.core.models import Company
from apps.customers.models import Customer, Node
from apps.customers.serializers import CustomerSerializer, NodeSerializer


class CompanyQuerySetMixin:
    def get_company(self):
        return Company.objects.filter(is_active=True).first()


class CustomerViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["full_name", "phone", "email", "address", "assigned_ip", "node__name", "status", "preferred_payment_method", "internal_notes"]
    filterset_fields = ["status", "customer_type", "node", "preferred_payment_method", "payment_day"]
    ordering_fields = ["full_name", "payment_day", "created_at"]

    def get_queryset(self):
        return Customer.objects.filter(company=self.get_company(), is_deleted=False).select_related("node")

    def perform_create(self, serializer):
        serializer.save(company=self.get_company(), created_by=self.request.user, updated_by=self.request.user)


class NodeViewSet(CompanyQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "zone", "code"]

    def get_queryset(self):
        return Node.objects.filter(company=self.get_company(), is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(company=self.get_company(), created_by=self.request.user, updated_by=self.request.user)
