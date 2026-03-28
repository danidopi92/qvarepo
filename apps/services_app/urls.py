from django.urls import path

from apps.services_app.views import CustomerServiceCreateView, CustomerServiceListView, CustomerServiceUpdateView

urlpatterns = [
    path("", CustomerServiceListView.as_view(), name="service-list"),
    path("new/", CustomerServiceCreateView.as_view(), name="service-create"),
    path("<int:pk>/edit/", CustomerServiceUpdateView.as_view(), name="service-update"),
]
