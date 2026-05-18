from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.views import ApiRootView, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/", ApiRootView.as_view(), name="api-root"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/customers/", include("apps.customers.urls")),
    path("api/organizations/", include("apps.organizations.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/receipts/", include("apps.receipts.urls")),
    path("api/reporting/", include("apps.reporting.urls")),
]
