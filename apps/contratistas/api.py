from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.activos.api import como_drf
from apps.usuarios.roles import VENTAS

from . import services
from .models import Contratista, Obra
from .serializers import ContratistaSerializer, ObraSerializer


class ContratistaViewSet(viewsets.ModelViewSet):
    queryset = Contratista.objects.prefetch_related("obras")
    serializer_class = ContratistaSerializer
    roles_escritura = (VENTAS,)
    roles_por_accion = {"desbloquear": (), "solicitar_desbloqueo": (VENTAS,)}
    filterset_fields = ["estado"]
    search_fields = ["rut", "razon_social", "contacto"]

    @action(detail=True, methods=["post"])
    def desbloquear(self, request, pk=None):
        c = self.get_object()
        como_drf(lambda: services.desbloquear(c, request.user, request.data.get("motivo", "")))
        return Response(self.get_serializer(c).data)

    @action(detail=True, methods=["post"], url_path="solicitar-desbloqueo")
    def solicitar_desbloqueo(self, request, pk=None):
        c = self.get_object()
        como_drf(lambda: services.solicitar_desbloqueo(c, request.user, request.data.get("motivo", "")))
        return Response({"detail": "Solicitud enviada al Administrador."})


class ObraViewSet(viewsets.ModelViewSet):
    queryset = Obra.objects.select_related("contratista")
    serializer_class = ObraSerializer
    roles_escritura = (VENTAS,)
    filterset_fields = ["contratista", "activa"]
    search_fields = ["nombre", "responsable_nombre"]
