from django.urls import path

from . import views

app_name = "mantenimiento"

urlpatterns = [
    path("", views.ListaView.as_view(), name="lista"),
    path("registrar/", views.RegistrarView.as_view(), name="registrar"),
]
