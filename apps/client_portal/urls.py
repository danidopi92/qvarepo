from django.urls import path

from apps.client_portal.views import (
    ClientPortalAccessView,
    ClientPortalDashboardView,
    ClientPortalHomeRedirectView,
    ClientPortalInvoiceListView,
    ClientPortalLoginView,
    ClientPortalLogoutView,
    ClientPortalPaymentListView,
    ClientPortalRecoveryView,
    ClientPortalRegisterView,
)

urlpatterns = [
    path("", ClientPortalHomeRedirectView.as_view(), name="portal-home"),
    path("access/", ClientPortalAccessView.as_view(), name="portal-access"),
    path("login/", ClientPortalLoginView.as_view(), name="portal-login"),
    path("register/", ClientPortalRegisterView.as_view(), name="portal-register"),
    path("recover/", ClientPortalRecoveryView.as_view(), name="portal-recover"),
    path("dashboard/", ClientPortalDashboardView.as_view(), name="portal-dashboard"),
    path("invoices/", ClientPortalInvoiceListView.as_view(), name="portal-invoices"),
    path("payments/", ClientPortalPaymentListView.as_view(), name="portal-payments"),
    path("logout/", ClientPortalLogoutView.as_view(), name="portal-logout"),
]
