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
                                "token": "/api/auth/token/",
                                "token_refresh": "/api/auth/token/refresh/",
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
                    "token": reverse("token-obtain"),
                    "token_refresh": reverse("token-refresh"),
                },
            }
        )
