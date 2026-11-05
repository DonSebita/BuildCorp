from rest_framework import serializers

from .models import Mantenimiento, PlanMantenimiento


class MantenimientoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source="activo.codigo", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    registrado_por = serializers.StringRelatedField()

    class Meta:
        model = Mantenimiento
        fields = [
            "id", "folio", "activo", "activo_codigo", "tipo", "tipo_display", "estado", "fecha", "horas_al_momento",
            "tecnico", "costo", "descripcion", "registrado_por",
        ]
        read_only_fields = ["folio", "registrado_por"]

    def create(self, validated_data):
        from .services import registrar_mantenimiento

        activo = validated_data.pop("activo")
        return registrar_mantenimiento(activo, self.context["request"].user, **validated_data)


class PlanSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source="activo.codigo", read_only=True)
    activo_nombre = serializers.CharField(source="activo.nombre", read_only=True)
    activo_estado = serializers.CharField(source="activo.estado", read_only=True)
    url = serializers.CharField(source="activo.get_absolute_url", read_only=True)

    class Meta:
        model = PlanMantenimiento
        fields = [
            "id", "activo", "activo_codigo", "activo_nombre", "activo_estado", "cada_usos", "cada_horas", "cada_dias",
            "ultima_fecha", "usos_restantes", "horas_restantes", "proxima_fecha", "dias_restantes", "vencido",
            "proxima", "situacion", "criterio", "url",
        ]
        read_only_fields = ["activo", "ultima_fecha"]
