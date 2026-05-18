from django.urls import path

from apps.receipts.views import (
    GenerateReceiptView,
    ReceiptDetailView,
    ReceiptListView,
    VerifyReceiptPublicView,
)

urlpatterns = [
    path("", ReceiptListView.as_view(), name="receipts-list"),
    path("generate/", GenerateReceiptView.as_view(), name="receipts-generate"),
    path("<int:receipt_id>/", ReceiptDetailView.as_view(), name="receipts-detail"),
    path("verify/<uuid:public_reference>/", VerifyReceiptPublicView.as_view(), name="receipts-verify-public"),
]
