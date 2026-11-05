from django.urls import path

from . import views

app_name = "contratistas"

urlpatterns = [
    path("", views.ListaView.as_view(), name="lista"),
    path("nuevo/", views.CrearView.as_view(), name="crear"),
    path("<int:pk>/", views.DetalleView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.EditarView.as_view(), name="editar"),
    path("<int:pk>/obras/nueva/", views.ObraCrearView.as_view(), name="obra_crear"),
    path("obras/<int:pk>/editar/", views.ObraEditarView.as_view(), name="obra_editar"),
    path("<int:pk>/bloqueo/", views.BloqueoView.as_view(), name="bloqueo"),
]
