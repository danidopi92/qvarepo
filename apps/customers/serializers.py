from rest_framework import serializers

from apps.customers.models import Customer, CustomerContact, CustomerNote, Node


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = "__all__"
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class CustomerNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerNote
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class CustomerSerializer(serializers.ModelSerializer):
    contacts = CustomerContactSerializer(many=True, read_only=True)
    notes = CustomerNoteSerializer(many=True, read_only=True)
    node_name = serializers.CharField(source="node.name", read_only=True)

    class Meta:
        model = Customer
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]
