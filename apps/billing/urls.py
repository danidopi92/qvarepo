from django.urls import path

from apps.billing.views import (
    BillingGenerateMonthlyView,
    DebtorsReportView,
    InvoiceCreateView,
    InvoiceDetailView,
    InvoiceListView,
    PaymentCreateView,
    PaymentListView,
    ReactivateCustomerView,
    SuspendCustomerView,
)

urlpatterns = [
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/new/", InvoiceCreateView.as_view(), name="invoice-create"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/generate-monthly/", BillingGenerateMonthlyView.as_view(), name="invoice-generate-monthly"),
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path("payments/new/", PaymentCreateView.as_view(), name="payment-create"),
    path("debtors/", DebtorsReportView.as_view(), name="debtors-report"),
    path("customers/<int:customer_id>/suspend/", SuspendCustomerView.as_view(), name="customer-suspend"),
    path("customers/<int:customer_id>/reactivate/", ReactivateCustomerView.as_view(), name="customer-reactivate"),
]
