import csv
from decimal import Decimal
from io import BytesIO, StringIO

from django.http import HttpResponse, StreamingHttpResponse
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.models import PaymentRequest, PaymentRequestStatus, PaymentTransaction, PaymentTransactionStatus
from apps.reporting.serializers import DashboardMetricsQuerySerializer, PaymentRequestExportQuerySerializer
from core.api.tenancy import resolve_request_organization_id


class DashboardMetricsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardMetricsQuerySerializer

    def get_organization_id_or_raise(self, request):
        organization_id = resolve_request_organization_id(request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id

    def get(self, request):
        params_serializer = self.get_serializer(data=request.query_params)
        params_serializer.is_valid(raise_exception=True)
        filters = params_serializer.validated_data

        organization_id = self.get_organization_id_or_raise(request)
        requests_qs = PaymentRequest.objects.filter(organization_id=organization_id)
        transactions_qs = PaymentTransaction.objects.filter(
            organization_id=organization_id,
            status=PaymentTransactionStatus.CONFIRMED,
        )

        customer_id = filters.get("customer_id")
        if customer_id:
            requests_qs = requests_qs.filter(customer_id=customer_id)
            transactions_qs = transactions_qs.filter(payment_request__customer_id=customer_id)

        service_id = filters.get("service_id")
        if service_id:
            requests_qs = requests_qs.filter(service_id=service_id)
            transactions_qs = transactions_qs.filter(payment_request__service_id=service_id)

        date_from = filters.get("date_from")
        if date_from:
            requests_qs = requests_qs.filter(created_at__date__gte=date_from)
            transactions_qs = transactions_qs.filter(payment_request__created_at__date__gte=date_from)

        date_to = filters.get("date_to")
        if date_to:
            requests_qs = requests_qs.filter(created_at__date__lte=date_to)
            transactions_qs = transactions_qs.filter(payment_request__created_at__date__lte=date_to)

        today = timezone.localdate()
        month_start = today.replace(day=1)
        zero_amount = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))

        remaining_amount_expr = Case(
            When(
                status__in=[PaymentRequestStatus.PENDING, PaymentRequestStatus.PARTIAL],
                expected_amount__gt=F("paid_amount"),
                then=ExpressionWrapper(
                    F("expected_amount") - F("paid_amount"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            ),
            default=zero_amount,
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        request_stats = requests_qs.aggregate(
            total_count=Count("id"),
            expected_total=Coalesce(Sum("expected_amount"), zero_amount),
            paid_total=Coalesce(Sum("paid_amount"), zero_amount),
            pending_count=Count("id", filter=Q(status=PaymentRequestStatus.PENDING)),
            partial_count=Count("id", filter=Q(status=PaymentRequestStatus.PARTIAL)),
            paid_count=Count("id", filter=Q(status=PaymentRequestStatus.PAID)),
            pending_expected_total=Coalesce(
                Sum("expected_amount", filter=Q(status=PaymentRequestStatus.PENDING)),
                zero_amount,
            ),
            partial_expected_total=Coalesce(
                Sum("expected_amount", filter=Q(status=PaymentRequestStatus.PARTIAL)),
                zero_amount,
            ),
            paid_expected_total=Coalesce(
                Sum("expected_amount", filter=Q(status=PaymentRequestStatus.PAID)),
                zero_amount,
            ),
            remaining_gap=Coalesce(Sum(remaining_amount_expr), zero_amount),
            overdue_count=Count(
                "id",
                filter=Q(
                    status__in=[PaymentRequestStatus.PENDING, PaymentRequestStatus.PARTIAL],
                    due_date__lt=today,
                ),
            ),
        )

        transaction_stats = transactions_qs.aggregate(
            today_transactions_count=Count("id", filter=Q(paid_at__date=today)),
            today_total_collected=Coalesce(
                Sum("amount_received", filter=Q(paid_at__date=today)),
                zero_amount,
            ),
            month_transactions_count=Count(
                "id",
                filter=Q(paid_at__date__gte=month_start, paid_at__date__lte=today),
            ),
            month_total_collected=Coalesce(
                Sum(
                    "amount_received",
                    filter=Q(paid_at__date__gte=month_start, paid_at__date__lte=today),
                ),
                zero_amount,
            ),
        )

        return Response(
            {
                "organization_id": organization_id,
                "filters": {
                    "customer_id": customer_id,
                    "service_id": service_id,
                    "date_from": date_from,
                    "date_to": date_to,
                },
                "today": {
                    "transactions_count": transaction_stats["today_transactions_count"],
                    "total_collected": transaction_stats["today_total_collected"],
                },
                "month": {
                    "transactions_count": transaction_stats["month_transactions_count"],
                    "total_collected": transaction_stats["month_total_collected"],
                },
                "requests": {
                    "total_count": request_stats["total_count"],
                    "expected_total": request_stats["expected_total"],
                    "paid_total": request_stats["paid_total"],
                    "remaining_gap": request_stats["remaining_gap"],
                    "overdue_count": request_stats["overdue_count"],
                    "by_status": {
                        "pending": {
                            "count": request_stats["pending_count"],
                            "expected_total": request_stats["pending_expected_total"],
                        },
                        "partial": {
                            "count": request_stats["partial_count"],
                            "expected_total": request_stats["partial_expected_total"],
                        },
                        "paid": {
                            "count": request_stats["paid_count"],
                            "expected_total": request_stats["paid_expected_total"],
                        },
                    },
                },
            }
        )


class PaymentRequestExportView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestExportQuerySerializer

    EXCEL_MAX_ROWS = 100_000
    PDF_MAX_ROWS = 3_000

    def get_organization_id_or_raise(self, request):
        organization_id = resolve_request_organization_id(request)
        if organization_id is None:
            raise ValidationError(
                {
                    "organization_id": "Aucune organisation active. Selectionnez une organisation via profil, query param ou header X-Organization-Id."
                }
            )
        return organization_id

    def get_filtered_queryset(self, organization_id, filters):
        queryset = (
            PaymentRequest.objects.filter(organization_id=organization_id)
            .select_related("customer", "service")
            .order_by("-created_at")
        )

        status_value = filters.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        customer_id = filters.get("customer_id")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        service_id = filters.get("service_id")
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        date_from = filters.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = filters.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    def build_export_rows(self, queryset):
        headers = [
            "request_id",
            "reference",
            "status",
            "expected_amount",
            "paid_amount",
            "remaining_amount",
            "customer_name",
            "customer_phone",
            "service_name",
            "due_date",
            "created_at",
        ]
        rows = []
        for item in queryset.iterator(chunk_size=1000):
            rows.append(
                [
                    item.id,
                    item.reference,
                    item.status,
                    str(item.expected_amount),
                    str(item.paid_amount),
                    str(item.remaining_amount),
                    item.customer.full_name,
                    item.customer.phone,
                    item.service.name,
                    item.due_date.isoformat() if item.due_date else "",
                    item.created_at.isoformat(),
                ]
            )
        return headers, rows

    def csv_stream(self, headers, rows):
        def generate():
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            for row in rows:
                writer.writerow(row)
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        return generate()

    def render_xlsx_bytes(self, headers, rows):
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise ValidationError({"detail": "Le package openpyxl est requis pour l'export Excel."}) from exc

        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet(title="payment_requests")
        sheet.append(headers)
        for row in rows:
            sheet.append(row)

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def render_pdf_bytes(self, headers, rows):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise ValidationError({"detail": "Le package reportlab est requis pour l'export PDF."}) from exc

        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=A4)
        width, height = A4
        y = height - 40
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, "CollectPay - Payment Requests Export")
        y -= 24
        pdf.setFont("Helvetica", 8)
        pdf.drawString(40, y, " | ".join(headers[:6]))
        y -= 18

        for row in rows:
            line = " | ".join(str(value) for value in row[:6])
            pdf.drawString(40, y, line[:130])
            y -= 12
            if y <= 40:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 8)

        pdf.save()
        return output.getvalue()

    def get(self, request):
        params_serializer = self.get_serializer(data=request.query_params)
        params_serializer.is_valid(raise_exception=True)
        filters = params_serializer.validated_data
        export_format = filters["export_format"]

        organization_id = self.get_organization_id_or_raise(request)
        queryset = self.get_filtered_queryset(organization_id=organization_id, filters=filters)
        row_count = queryset.count()

        if export_format == "xlsx" and row_count > self.EXCEL_MAX_ROWS:
            raise ValidationError(
                {
                    "detail": f"Export Excel limite a {self.EXCEL_MAX_ROWS} lignes. Appliquez plus de filtres."
                }
            )
        if export_format == "pdf" and row_count > self.PDF_MAX_ROWS:
            raise ValidationError(
                {"detail": f"Export PDF limite a {self.PDF_MAX_ROWS} lignes. Appliquez plus de filtres."}
            )

        headers, rows = self.build_export_rows(queryset)
        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        filename = f"payment-requests-{timestamp}"

        if export_format == "csv":
            response = StreamingHttpResponse(
                self.csv_stream(headers, rows),
                content_type="text/csv; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return response

        if export_format == "xlsx":
            payload = self.render_xlsx_bytes(headers, rows)
            response = HttpResponse(
                payload,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return response

        payload = self.render_pdf_bytes(headers, rows)
        response = HttpResponse(payload, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
        return response
