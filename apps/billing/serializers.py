from rest_framework import serializers

from apps.billing.models import Invoice, InvoiceItem, Payment, SuspensionEvent


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at", "line_total"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Invoice
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = [
            "company", "created_by", "updated_by", "created_at", "updated_at",
            "invoice_number", "status", "total_amount", "amount_paid", "balance_due",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Payment
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at", "registered_by"]


class SuspensionEventSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = SuspensionEvent
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]
