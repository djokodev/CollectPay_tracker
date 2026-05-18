from django.urls import path

from apps.backoffice.views import (
    BackofficeHomeView,
    BackofficeKpiCardsPartialView,
    BackofficePaymentRequestsPartialView,
)

urlpatterns = [
    path("", BackofficeHomeView.as_view(), name="backoffice-home"),
    path(
        "partials/kpi-cards/",
        BackofficeKpiCardsPartialView.as_view(),
        name="backoffice-kpi-cards",
    ),
    path(
        "partials/payment-requests/",
        BackofficePaymentRequestsPartialView.as_view(),
        name="backoffice-payment-requests-partial",
    ),
]
