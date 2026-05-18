from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def health_check(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "collectpay-tracker",
            "version": settings.SPECTACULAR_SETTINGS.get("VERSION"),
        }
    )


class ApiRootView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="API root metadata",
                examples=[
                    OpenApiExample(
                        "API Root",
                        value={
                            "name": "CollectPay Tracker API",
                            "version": "0.1.0",
                            "endpoints": {
                                "health": "/health/",
                                "schema": "/api/schema/",
                                "docs": "/api/docs/",
                                "login": "/api/auth/login/",
                                "token_refresh": "/api/auth/refresh/",
                                "register": "/api/auth/register/",
                                "profile": "/api/auth/profile/",
                                "users": "/api/auth/users/",
                                "my_permissions": "/api/auth/my-permissions/",
                                "organizations": "/api/organizations/",
                                "my_organizations": "/api/organizations/mine/",
                                "switch_active_organization": "/api/organizations/switch-active/",
                                "customers": "/api/customers/",
                                "services": "/api/catalog/services/",
                                "payment_requests": "/api/payments/requests/",
                                "payment_transactions": "/api/payments/transactions/",
                            },
                        },
                    )
                ],
            )
        }
    )
    def get(self, request):
        return Response(
            {
                "name": "CollectPay Tracker API",
                "version": settings.SPECTACULAR_SETTINGS.get("VERSION"),
                "endpoints": {
                    "health": reverse("health-check"),
                    "schema": reverse("schema"),
                    "docs": reverse("swagger-ui"),
                    "login": reverse("auth-login"),
                    "token_refresh": reverse("auth-refresh"),
                    "register": reverse("auth-register"),
                    "profile": reverse("auth-profile"),
                    "users": reverse("auth-users-list"),
                    "my_permissions": reverse("auth-my-permissions"),
                    "organizations": reverse("organizations-list-create"),
                    "my_organizations": reverse("organizations-mine"),
                    "switch_active_organization": reverse("organizations-switch-active"),
                    "customers": reverse("customers-list-create"),
                    "services": reverse("services-list-create"),
                    "payment_requests": reverse("payment-requests-list-create"),
                    "payment_transactions": reverse("payment-transactions-list-create"),
                },
            }
        )
