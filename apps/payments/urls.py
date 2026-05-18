from django.urls import path

from apps.payments.views import (
    ApplyManualPaymentView,
    CancelPaymentRequestView,
    OverduePaymentRequestsView,
    PartialPaymentRequestsView,
    PaymentRequestDetailView,
    PaymentRequestListCreateView,
    PaymentRequestTransactionsView,
    PaymentTransactionListCreateView,
    PendingPaymentRequestsView,
)

urlpatterns = [
    path("requests/", PaymentRequestListCreateView.as_view(), name="payment-requests-list-create"),
    path("requests/<int:id>/", PaymentRequestDetailView.as_view(), name="payment-requests-detail"),
    path("requests/pending/", PendingPaymentRequestsView.as_view(), name="payment-requests-pending"),
    path("requests/partial/", PartialPaymentRequestsView.as_view(), name="payment-requests-partial"),
    path("requests/overdue/", OverduePaymentRequestsView.as_view(), name="payment-requests-overdue"),
    path(
        "requests/<int:payment_request_id>/cancel/",
        CancelPaymentRequestView.as_view(),
        name="payment-requests-cancel",
    ),
    path(
        "requests/<int:payment_request_id>/apply-manual-payment/",
        ApplyManualPaymentView.as_view(),
        name="payment-requests-apply-manual-payment",
    ),
    path(
        "requests/<int:payment_request_id>/transactions/",
        PaymentRequestTransactionsView.as_view(),
        name="payment-request-transactions",
    ),
    path("transactions/", PaymentTransactionListCreateView.as_view(), name="payment-transactions-list-create"),
]
