from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.activos.api import como_drf
from apps.usuarios.roles import ENCARGADO, VENTAS

from . import services
from .models import Cobro, Prestamo, PrestamoPaquete
from .serializers import (
    CobroSerializer, FirmaEntradaSerializer, PrestamoEntradaSerializer, PrestamoListaSerializer, PrestamoSerializer,
)


def ip_de(request):
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
    return reenviada.split(",")[0].strip() if reenviada else request.META.get("REMOTE_ADDR")


class PrestamoFilter(filters.FilterSet):
    desde = filters.DateFilter(field_name="fecha_entrega", lookup_expr="gte")
    hasta = filters.DateFilter(field_name="fecha_entrega", lookup_expr="lte")

    class Meta:
        model = Prestamo
        fields = {"estado": ["exact", "in"], "contratista": ["exact"], "obra": ["exact"]}


class PrestamoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Prestamo.objects.select_related("contratista", "obra").prefetch_related(
        "paquetes__paquete__items", "detalles__activo__categoria", "firmas"
    )
    filterset_class = PrestamoFilter
    search_fields = ["codigo", "contratista__razon_social", "obra__nombre"]
    ordering_fields = ["codigo", "fecha_entrega", "fecha_devolucion_pactada"]
    roles_por_accion = {
        "create": (VENTAS,), "cotizar": (VENTAS,),
        "asignar_activos": (ENCARGADO,), "quitar_activo": (ENCARGADO,),
        "entregar": (ENCARGADO,), "devolver": (ENCARGADO,),
    }

    def get_serializer_class(self):
        return PrestamoListaSerializer if self.action in ("list", "atrasados") else PrestamoSerializer

    def _entrada(self, request, completa):
        s = PrestamoEntradaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if completa and not (d.get("contratista") and d.get("obra")):
            raise ValidationError({"detail": "Elige el contratista y la obra."})
        return d

    @action(detail=False, methods=["post"])
    def cotizar(self, request):
        d = self._entrada(request, completa=False)
        return Response(como_drf(lambda: services.cotizar(
            d["fecha_entrega"], d["fecha_devolucion_pactada"], d.get("paquetes", []), d.get("activos", []))))

    def create(self, request):
        d = self._entrada(request, completa=True)
        p = como_drf(lambda: services.crear_prestamo(
            request.user, d["contratista"], d["obra"], d["fecha_entrega"], d["fecha_devolucion_pactada"],
            d.get("paquetes", []), d.get("activos", []), d.get("observaciones", ""),
        ))
        return Response(PrestamoSerializer(p).data, status=201)

    @action(detail=True, methods=["post"], url_path="asignar-activos")
    def asignar_activos(self, request, pk=None):
        prestamo = self.get_object()
        pp = get_object_or_404(PrestamoPaquete, pk=request.data.get("prestamo_paquete"), prestamo=prestamo)
        codigos = request.data.get("codigos") or []
        if isinstance(codigos, str):
            codigos = [codigos]
        como_drf(lambda: services.asignar_activos(prestamo, pp, codigos))
        return Response(PrestamoSerializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="quitar-activo")
    def quitar_activo(self, request, pk=None):
        prestamo = self.get_object()
        detalle = get_object_or_404(prestamo.detalles, pk=request.data.get("detalle"))
        como_drf(lambda: services.quitar_activo(prestamo, detalle))
        return Response(PrestamoSerializer(self.get_object()).data)

    def _firma(self, request):
        s = FirmaEntradaSerializer(data=request.data.get("firma") or {})
        s.is_valid(raise_exception=True)
        return s.validated_data

    @action(detail=True, methods=["post"])
    def entregar(self, request, pk=None):
        prestamo, firma = self.get_object(), self._firma(request)
        como_drf(lambda: services.entregar(prestamo, request.user, request.data.get("checklist") or {}, firma, ip_de(request)))
        return Response(PrestamoSerializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        prestamo, firma = self.get_object(), self._firma(request)
        como_drf(lambda: services.devolver(prestamo, request.user, request.data.get("recepcion") or {}, firma, ip_de(request)))
        return Response(PrestamoSerializer(self.get_object()).data)

    @action(detail=False)
    def atrasados(self, request):
        qs = self.filter_queryset(self.get_queryset()).filter(estado=Prestamo.Estado.ATRASADO)
        return Response(self.get_serializer(qs, many=True).data)


class CobroViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cobro.objects.select_related("prestamo__contratista")
    serializer_class = CobroSerializer
    roles_lectura = (VENTAS,)
    roles_por_accion = {"pagar": (VENTAS,)}
    filterset_fields = ["estado"]

    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        cobro = self.get_object()
        como_drf(lambda: services.registrar_pago(cobro, request.user))
        return Response(self.get_serializer(cobro).data)
