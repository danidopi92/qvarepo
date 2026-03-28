from rest_framework import serializers

from apps.integrations.models import IntegrationEvent


class IntegrationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationEvent
        exclude = ["is_deleted", "deleted_at", "deleted_by"]
        read_only_fields = ["company", "created_by", "updated_by", "created_at", "updated_at"]


class OpenClawActionSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False)
    service_id = serializers.IntegerField(required=False)
    action = serializers.CharField(required=False, allow_blank=True)
    payload = serializers.JSONField(required=False)
    command = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("customer_id") and not attrs.get("payload"):
            raise serializers.ValidationError("Debe enviar customer_id o payload.")
        return attrs
