from django.urls import path

from . import views

app_name = "prestamos"

urlpatterns = [
    path("", views.ListaView.as_view(), name="lista"),
    path("nuevo/", views.NuevoView.as_view(), name="nuevo"),
    path("cobros/", views.CobrosView.as_view(), name="cobros"),
    path("cobros/<int:pk>/", views.CobroView.as_view(), name="cobro"),
    path("cobros/<int:pk>/pagar/", views.PagarView.as_view(), name="pagar"),
    path("parametros/", views.ParametrosView.as_view(), name="parametros"),
    path("<str:codigo>/", views.DetalleView.as_view(), name="detalle"),
    path("<str:codigo>/entregar/", views.EntregarView.as_view(), name="entregar"),
    path("<str:codigo>/devolver/", views.DevolverView.as_view(), name="devolver"),
    path("<str:codigo>/comprobante/", views.ComprobanteView.as_view(), name="comprobante"),
    path("<str:codigo>/qr.png", views.QRView.as_view(), name="qr"),
    path("<str:codigo>/etiqueta/", views.EtiquetaView.as_view(), name="etiqueta"),
]
