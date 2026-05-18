from django.urls import path

from apps.reporting.views import DashboardMetricsView, PaymentRequestExportView

urlpatterns = [
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="reporting-dashboard-metrics"),
    path("exports/payment-requests/", PaymentRequestExportView.as_view(), name="reporting-export-payment-requests"),
]
