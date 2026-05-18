from django.urls import path

from apps.catalog.views import ServiceDeactivateView, ServiceDetailView, ServiceListCreateView

urlpatterns = [
    path("services/", ServiceListCreateView.as_view(), name="services-list-create"),
    path("services/<int:id>/", ServiceDetailView.as_view(), name="services-detail"),
    path("services/<int:service_id>/deactivate/", ServiceDeactivateView.as_view(), name="services-deactivate"),
]
