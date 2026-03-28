from django.urls import path

from apps.integrations.views import IntegrationEventListView

urlpatterns = [
    path("events/", IntegrationEventListView.as_view(), name="integration-event-list"),
]
