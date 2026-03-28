from django.urls import path

from apps.customers.views import (
    CustomerBulkDeleteFilteredView,
    CustomerBulkDeleteView,
    CustomerBulkPermanentDeleteView,
    CustomerBulkRestoreView,
    CustomerCreateView,
    CustomerDeleteView,
    CustomerPermanentDeleteView,
    CustomerPortalAccountToggleView,
    CustomerRestoreAllView,
    CustomerRestoreView,
    DeletedCustomerListView,
    CustomerDetailView,
    CustomerExportTemplateView,
    CustomerImportView,
    CustomerListView,
    CustomerUpdateView,
)

urlpatterns = [
    path("", CustomerListView.as_view(), name="customer-list"),
    path("deleted/", DeletedCustomerListView.as_view(), name="customer-deleted-list"),
    path("new/", CustomerCreateView.as_view(), name="customer-create"),
    path("import/", CustomerImportView.as_view(), name="customer-import"),
    path("export-template/", CustomerExportTemplateView.as_view(), name="customer-export-template"),
    path("bulk-delete/", CustomerBulkDeleteView.as_view(), name="customer-bulk-delete"),
    path("bulk-delete-filtered/", CustomerBulkDeleteFilteredView.as_view(), name="customer-bulk-delete-filtered"),
    path("bulk-permanent-delete/", CustomerBulkPermanentDeleteView.as_view(), name="customer-bulk-permanent-delete"),
    path("bulk-restore/", CustomerBulkRestoreView.as_view(), name="customer-bulk-restore"),
    path("restore-filtered/", CustomerRestoreAllView.as_view(), name="customer-restore-filtered"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path("<int:pk>/portal-account/toggle/", CustomerPortalAccountToggleView.as_view(), name="customer-portal-account-toggle"),
    path("<int:pk>/edit/", CustomerUpdateView.as_view(), name="customer-update"),
    path("<int:pk>/delete/", CustomerDeleteView.as_view(), name="customer-delete"),
    path("<int:pk>/permanent-delete/", CustomerPermanentDeleteView.as_view(), name="customer-permanent-delete"),
    path("<int:pk>/restore/", CustomerRestoreView.as_view(), name="customer-restore"),
]
