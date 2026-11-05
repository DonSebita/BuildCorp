from django.urls import path

from . import views

app_name = "alertas"

urlpatterns = [
    path("", views.BandejaView.as_view(), name="lista"),
]
