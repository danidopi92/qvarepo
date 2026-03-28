from django.urls import path

from apps.reports.views import ReportsHomeView, export_customers_csv, export_debtors_csv, export_income_excel

urlpatterns = [
    path("", ReportsHomeView.as_view(), name="reports-home"),
    path("debtors.csv", export_debtors_csv, name="report-debtors-csv"),
    path("income.xlsx", export_income_excel, name="report-income-excel"),
    path("customers.csv", export_customers_csv, name="report-customers-csv"),
]
