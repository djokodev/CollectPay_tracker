from django.urls import path

from apps.reporting.views import DashboardMetricsView

urlpatterns = [
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="reporting-dashboard-metrics"),
]
