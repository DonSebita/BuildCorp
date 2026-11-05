from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("exportar/<str:recurso>.csv", views.ExportarCSVView.as_view(), name="exportar"),
]
