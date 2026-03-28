from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.billing.api import InvoiceViewSet, PaymentViewSet, SuspensionEventViewSet
from apps.core.auth_views import RateLimitedLoginView
from apps.customers.api import CustomerViewSet, NodeViewSet
from apps.integrations.api import IntegrationEventViewSet, OpenClawActionViewSet
from apps.services_app.api import CustomerServiceViewSet, ServicePlanViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="api-customers")
router.register("nodes", NodeViewSet, basename="api-nodes")
router.register("services", CustomerServiceViewSet, basename="api-services")
router.register("plans", ServicePlanViewSet, basename="api-plans")
router.register("invoices", InvoiceViewSet, basename="api-invoices")
router.register("payments", PaymentViewSet, basename="api-payments")
router.register("suspensions", SuspensionEventViewSet, basename="api-suspensions")
router.register("integration-events", IntegrationEventViewSet, basename="api-integration-events")
router.register("openclaw", OpenClawActionViewSet, basename="api-openclaw")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", RateLimitedLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
    path("portal/", include("apps.client_portal.urls")),
    path("customers/", include("apps.customers.urls")),
    path("services/", include("apps.services_app.urls")),
    path("billing/", include("apps.billing.urls")),
    path("integrations/", include("apps.integrations.urls")),
    path("reports/", include("apps.reports.urls")),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
