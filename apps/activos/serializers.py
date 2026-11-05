from rest_framework import serializers

from apps.activos import services

from .models import Activo, Bodega, CategoriaActivo, HistorialEstado, ItemPaquete, PaqueteMaquinaria, Traslado


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaActivo
        fields = "__all__"
        read_only_fields = ["ultimo_correlativo"]


class BodegaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Bodega
        fields = ["id", "nombre", "tipo", "tipo_display", "direccion", "obra", "encargado"]


class ActivoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega_actual.nombre", read_only=True, default=None)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    mantencion = serializers.SerializerMethodField()
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Activo
        fields = [
            "id", "codigo", "nombre", "categoria", "categoria_nombre", "marca", "modelo", "numero_serie",
            "fecha_adquisicion", "valor_compra", "estado", "estado_display", "bodega_actual", "bodega_nombre",
            "horas_uso_totales", "usos_totales", "usos_desde_mantencion", "activo", "mantencion", "url",
        ]
        read_only_fields = ["codigo", "estado", "horas_uso_totales", "usos_totales", "usos_desde_mantencion"]

    def get_mantencion(self, obj):
        plan = getattr(obj, "plan", None)
        if plan is None:
            return None
        return {"situacion": plan.situacion, "criterio": plan.criterio}

    def create(self, validated_data):
        return services.crear_activo(self.context["request"].user, **validated_data)


class HistorialSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()

    class Meta:
        model = HistorialEstado
        fields = ["fecha", "estado_anterior", "estado_nuevo", "usuario", "motivo", "referencia"]


class TrasladoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source="activo.codigo", read_only=True)
    bodega_origen = serializers.StringRelatedField()
    bodega_destino = serializers.StringRelatedField()
    usuario = serializers.StringRelatedField()

    class Meta:
        model = Traslado
        fields = ["fecha", "activo_codigo", "bodega_origen", "bodega_destino", "usuario", "observacion"]


class ItemPaqueteSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = ItemPaquete
        fields = ["id", "categoria", "categoria_nombre", "cantidad"]


class PaqueteSerializer(serializers.ModelSerializer):
    items = ItemPaqueteSerializer(many=True)

    class Meta:
        model = PaqueteMaquinaria
        fields = ["id", "codigo", "nombre", "descripcion", "tarifa_diaria", "tarifa_mensual", "activo", "items"]

    def create(self, validated_data):
        items = validated_data.pop("items")
        paquete = PaqueteMaquinaria.objects.create(creado_por=self.context["request"].user, **validated_data)
        for item in items:
            ItemPaquete.objects.create(paquete=paquete, **item)
        return paquete

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        instance = super().update(instance, validated_data)
        if items is not None:
            instance.items.all().delete()
            for item in items:
                ItemPaquete.objects.create(paquete=instance, **item)
        return instance
