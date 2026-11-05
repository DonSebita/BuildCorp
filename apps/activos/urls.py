from django.urls import path

from . import views

app_name = "activos"

urlpatterns = [
    path("", views.ListaView.as_view(), name="lista"),
    path("nuevo/", views.CrearView.as_view(), name="crear"),
    path("escanear/", views.EscanearView.as_view(), name="escanear"),
    path("etiquetas/", views.EtiquetasView.as_view(), name="etiquetas"),
    path("bodegas/", views.BodegasView.as_view(), name="bodegas"),
    path("paquetes/", views.PaquetesView.as_view(), name="paquetes"),
    path("paquetes/nuevo/", views.PaqueteCrearView.as_view(), name="paquete_crear"),
    path("paquetes/<int:pk>/editar/", views.PaqueteEditarView.as_view(), name="paquete_editar"),
    path("<str:codigo>/", views.FichaView.as_view(), name="ficha"),
    path("<str:codigo>/editar/", views.EditarView.as_view(), name="editar"),
    path("<str:codigo>/qr.png", views.QRView.as_view(), name="qr"),
    path("<str:codigo>/solicitar-baja/", views.SolicitarBajaView.as_view(), name="solicitar_baja"),
]
