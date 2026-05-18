from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView, View
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from apps.organizations.models import OrganizationMembership
from apps.payments.models import PaymentRequest, PaymentRequestStatus, PaymentTransaction, PaymentTransactionStatus


def _resolve_user_from_bearer(request):
    authenticator = JWTAuthentication()
    try:
        user_auth = authenticator.authenticate(request)
    except (AuthenticationFailed, InvalidToken):
        return None
    if not user_auth:
        return None
    user, _token = user_auth
    return user


def _resolve_organization_id(user, request):
    allowed_org_ids = list(
        OrganizationMembership.objects.filter(user=user, is_active=True).values_list(
            "organization_id", flat=True
        )
    )
    if not allowed_org_ids:
        return None

    requested = request.GET.get("organization_id") or request.POST.get("organization_id")
    if requested:
        try:
            requested_id = int(requested)
        except (TypeError, ValueError):
            return None
        if requested_id in allowed_org_ids:
            return requested_id
        return None

    active_org_id = getattr(getattr(user, "account_profile", None), "active_organization_id", None)
    if active_org_id in allowed_org_ids:
        return active_org_id
    return sorted(allowed_org_ids)[0]


class BackofficeJWTContextMixin:
    def get_user_and_org_or_response(self, request):
        user = _resolve_user_from_bearer(request)
        if not user:
            return None, JsonResponse(
                {"detail": "Authentification requise (Bearer token)."},
                status=401,
            )

        organization_id = _resolve_organization_id(user, request)
        if organization_id is None:
            return None, JsonResponse(
                {"detail": "Organisation active introuvable ou non autorisee."},
                status=400,
            )

        return (user, organization_id), None


class BackofficeHomeView(TemplateView):
    template_name = "backoffice/index.html"


class BackofficeKpiCardsPartialView(BackofficeJWTContextMixin, TemplateView):
    template_name = "backoffice/partials/kpi_cards.html"

    def get(self, request, *args, **kwargs):
        context_key, error_response = self.get_user_and_org_or_response(request)
        if error_response:
            return error_response

        _user, organization_id = context_key
        today = timezone.localdate()
        month_start = today.replace(day=1)
        zero = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))

        requests_qs = PaymentRequest.objects.filter(organization_id=organization_id)
        transactions_qs = PaymentTransaction.objects.filter(
            organization_id=organization_id,
            status=PaymentTransactionStatus.CONFIRMED,
        )

        request_stats = requests_qs.aggregate(
            pending_count=Count("id", filter=Q(status=PaymentRequestStatus.PENDING)),
            partial_count=Count("id", filter=Q(status=PaymentRequestStatus.PARTIAL)),
            paid_count=Count("id", filter=Q(status=PaymentRequestStatus.PAID)),
            expected_total=Coalesce(Sum("expected_amount"), zero),
            paid_total=Coalesce(Sum("paid_amount"), zero),
            remaining_gap=Coalesce(
                Sum(
                    F("expected_amount") - F("paid_amount"),
                    filter=Q(status__in=[PaymentRequestStatus.PENDING, PaymentRequestStatus.PARTIAL]),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                zero,
            ),
        )
        tx_stats = transactions_qs.aggregate(
            today_collected=Coalesce(Sum("amount_received", filter=Q(paid_at__date=today)), zero),
            month_collected=Coalesce(
                Sum(
                    "amount_received",
                    filter=Q(paid_at__date__gte=month_start, paid_at__date__lte=today),
                ),
                zero,
            ),
        )

        context = {
            "organization_id": organization_id,
            "pending_count": request_stats["pending_count"],
            "partial_count": request_stats["partial_count"],
            "paid_count": request_stats["paid_count"],
            "today_collected": tx_stats["today_collected"],
            "month_collected": tx_stats["month_collected"],
            "expected_total": request_stats["expected_total"],
            "paid_total": request_stats["paid_total"],
            "remaining_gap": request_stats["remaining_gap"],
        }
        return self.render_to_response(context)


class BackofficePaymentRequestsPartialView(BackofficeJWTContextMixin, TemplateView):
    template_name = "backoffice/partials/payment_requests_table.html"

    def get(self, request, *args, **kwargs):
        context_key, error_response = self.get_user_and_org_or_response(request)
        if error_response:
            return error_response

        _user, organization_id = context_key
        queryset = (
            PaymentRequest.objects.filter(organization_id=organization_id)
            .select_related("customer", "service")
            .order_by("-created_at")
        )

        status_filter = request.GET.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        customer_id = request.GET.get("customer_id")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        service_id = request.GET.get("service_id")
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        search = request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(service__name__icontains=search)
            )

        payment_requests = list(queryset[:25])
        context = {
            "organization_id": organization_id,
            "payment_requests": payment_requests,
            "total_count": queryset.count(),
        }
        return self.render_to_response(context)


class BackofficeAuthProbeView(BackofficeJWTContextMixin, View):
    def get(self, request, *args, **kwargs):
        context_key, error_response = self.get_user_and_org_or_response(request)
        if error_response:
            return error_response

        user, organization_id = context_key
        return JsonResponse(
            {
                "username": user.username,
                "organization_id": organization_id,
            }
        )
