from rest_framework import serializers

from apps.services_app.models import CustomerService, Equipment, ServicePlan


class ServicePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePlan
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class CustomerServiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = CustomerService
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]
