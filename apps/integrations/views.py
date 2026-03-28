from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.integrations.models import IntegrationEvent


class IntegrationEventListView(LoginRequiredMixin, ListView):
    model = IntegrationEvent
    template_name = "integrations/list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        return IntegrationEvent.objects.filter(is_deleted=False).select_related("customer")
