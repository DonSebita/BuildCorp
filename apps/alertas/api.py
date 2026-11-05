from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.roles import TODOS

from .models import Alerta
from .services import alertas_para


class AlertaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    enlace = serializers.CharField(read_only=True)

    class Meta:
        model = Alerta
        fields = ["id", "tipo", "tipo_display", "nivel", "mensaje", "rol_destino", "leida", "resuelta", "fecha", "enlace"]


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaSerializer
    queryset = Alerta.objects.none()
    roles_por_accion = {"marcar_leida": TODOS, "resolver": TODOS}
    filterset_fields = ["tipo", "nivel", "leida", "resuelta"]

    def get_queryset(self):
        return alertas_para(self.request.user).prefetch_related("objeto")

    @action(detail=True, methods=["post"], url_path="marcar-leida")
    def marcar_leida(self, request, pk=None):
        alerta = self.get_object()
        alerta.leida = True
        alerta.save(update_fields=["leida"])
        return Response(self.get_serializer(alerta).data)

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        alerta.leida = alerta.resuelta = True
        alerta.save(update_fields=["leida", "resuelta"])
        return Response(self.get_serializer(alerta).data)
