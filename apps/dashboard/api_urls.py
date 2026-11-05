from django.urls import path

from .api import ResumenView

urlpatterns = [
    path("dashboard/resumen/", ResumenView.as_view(), name="api-dashboard-resumen"),
]
