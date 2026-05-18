from django.urls import path

from apps.customers.views import (
    CustomerDeactivateView,
    CustomerDetailView,
    CustomerListCreateView,
    CustomerPaymentHistoryView,
)

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="customers-list-create"),
    path("<int:id>/", CustomerDetailView.as_view(), name="customers-detail"),
    path("<int:customer_id>/deactivate/", CustomerDeactivateView.as_view(), name="customers-deactivate"),
    path("<int:customer_id>/history/", CustomerPaymentHistoryView.as_view(), name="customers-history"),
]
