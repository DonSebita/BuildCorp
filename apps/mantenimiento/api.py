from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.activos.api import como_drf
from apps.usuarios.roles import BODEGUERO, ENCARGADO, VENTAS

from .models import Mantenimiento, PlanMantenimiento
from .serializers import MantenimientoSerializer, PlanSerializer

LECTURA = (BODEGUERO, ENCARGADO, VENTAS)


class MantenimientoViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Mantenimiento.objects.select_related("activo", "registrado_por")
    serializer_class = MantenimientoSerializer
    roles_lectura = LECTURA
    roles_escritura = (BODEGUERO,)
    filterset_fields = ["activo", "tipo", "estado"]
    search_fields = ["folio", "activo__codigo", "tecnico"]

    def perform_create(self, serializer):
        como_drf(lambda: serializer.save())


class PlanViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PlanMantenimiento.objects.select_related("activo").exclude(activo__estado="DADO_DE_BAJA")
    serializer_class = PlanSerializer
    roles_lectura = LECTURA
    roles_escritura = ()  # el Admin ajusta el plan de un activo

    @action(detail=False)
    def proximos(self, request):
        planes = [p for p in self.get_queryset() if p.situacion != "AL_DIA"]
        planes.sort(key=lambda p: (p.situacion != "VENCIDO", p.criterio))
        return Response(self.get_serializer(planes, many=True).data)
