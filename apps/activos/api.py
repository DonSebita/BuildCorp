from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.usuarios.roles import ADMIN, BODEGUERO, VENTAS, rol_de

from . import services
from .models import Activo, Bodega, CategoriaActivo, PaqueteMaquinaria
from .serializers import (
    ActivoSerializer, BodegaSerializer, CategoriaSerializer, HistorialSerializer, PaqueteSerializer,
    TrasladoSerializer,
)


def como_drf(fn):
    """Convierte los ValidationError de la capa de servicios en errores 400 de DRF."""
    try:
        return fn()
    except DjangoValidationError as e:
        raise ValidationError({"detail": " ".join(e.messages)})


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaActivo.objects.all()
    serializer_class = CategoriaSerializer
    roles_escritura = ()
    search_fields = ["nombre", "prefijo_codigo"]


class BodegaViewSet(viewsets.ModelViewSet):
    queryset = Bodega.objects.all()
    serializer_class = BodegaSerializer
    roles_escritura = (BODEGUERO,)

    @action(detail=True)
    def inventario(self, request, pk=None):
        activos = self.get_object().activos.filter(activo=True).select_related("categoria", "plan")
        return Response(ActivoSerializer(activos, many=True, context={"request": request}).data)


class ActivoFilter(filters.FilterSet):
    class Meta:
        model = Activo
        fields = {"estado": ["exact", "in"], "categoria": ["exact"], "bodega_actual": ["exact"], "activo": ["exact"]}


class ActivoViewSet(viewsets.ModelViewSet):
    queryset = Activo.objects.select_related("categoria", "bodega_actual", "plan")
    serializer_class = ActivoSerializer
    filterset_class = ActivoFilter
    search_fields = ["codigo", "nombre", "marca", "modelo", "numero_serie"]
    ordering_fields = ["codigo", "nombre", "estado", "usos_desde_mantencion"]
    roles_escritura = (BODEGUERO,)
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        activo = self.get_object()
        nuevo = request.data.get("estado")
        motivo = (request.data.get("motivo") or "").strip()
        if nuevo == Activo.Estado.DADO_DE_BAJA:
            if rol_de(request.user) != ADMIN:
                raise PermissionDenied("Solo el Administrador da de baja. El bodeguero puede solicitarlo.")
            como_drf(lambda: services.dar_de_baja(activo, request.user, motivo))
        elif nuevo == Activo.Estado.MANTENIMIENTO:
            como_drf(lambda: services.enviar_a_mantenimiento(activo, request.user, motivo or "Envío manual"))
        else:
            como_drf(lambda: services.cambiar_estado(activo, nuevo, request.user, motivo))
        return Response(self.get_serializer(activo).data)

    @action(detail=True, url_path="hoja-vida")
    def hoja_vida(self, request, pk=None):
        from apps.mantenimiento.serializers import MantenimientoSerializer

        activo = self.get_object()
        return Response({
            "activo": self.get_serializer(activo).data,
            "historial": HistorialSerializer(activo.historial.select_related("usuario"), many=True).data,
            "traslados": TrasladoSerializer(activo.traslados.all(), many=True).data,
            "mantenimientos": MantenimientoSerializer(activo.mantenimientos.all(), many=True).data,
        })

    @action(detail=True, methods=["post"])
    def trasladar(self, request, pk=None):
        activo = self.get_object()
        destino = get_object_or_404(Bodega, pk=request.data.get("bodega_destino"))
        t = como_drf(lambda: services.trasladar(activo, destino, request.user, request.data.get("observacion", "")))
        return Response(TrasladoSerializer(t).data, status=201)

    @action(detail=False, url_path=r"codigo/(?P<codigo>[A-Za-z0-9-]+)")
    def por_codigo(self, request, codigo=None):
        activo = get_object_or_404(self.get_queryset(), codigo=codigo.strip().upper())
        return Response(self.get_serializer(activo).data)

    @action(detail=True)
    def qr(self, request, pk=None):
        return HttpResponse(services.qr_png(self.get_object(), request), content_type="image/png")


class PaqueteViewSet(viewsets.ModelViewSet):
    queryset = PaqueteMaquinaria.objects.prefetch_related("items__categoria")
    serializer_class = PaqueteSerializer
    roles_escritura = (VENTAS,)
    search_fields = ["codigo", "nombre"]

    @action(detail=True)
    def disponibilidad(self, request, pk=None):
        return Response(services.disponibilidad_paquete(self.get_object()))
