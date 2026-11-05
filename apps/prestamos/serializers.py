from rest_framework import serializers

from apps.activos.models import Activo, PaqueteMaquinaria
from apps.contratistas.models import Contratista, Obra

from .models import Cobro, DetallePrestamo, Firma, Prestamo, PrestamoPaquete


class DetalleSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="activo.codigo", read_only=True)
    nombre = serializers.CharField(source="activo.nombre", read_only=True)
    categoria = serializers.CharField(source="activo.categoria.nombre", read_only=True)
    requiere_horometro = serializers.BooleanField(source="activo.categoria.requiere_horometro", read_only=True)
    horas_actuales = serializers.DecimalField(source="activo.horas_uso_totales", max_digits=9, decimal_places=1, read_only=True)

    class Meta:
        model = DetallePrestamo
        fields = [
            "id", "codigo", "nombre", "categoria", "requiere_horometro", "horas_actuales", "prestamo_paquete",
            "horometro_salida", "horometro_llegada", "estado_salida", "estado_llegada", "observacion_dano", "cargo_dano",
        ]


class PrestamoPaqueteSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="paquete.nombre", read_only=True)
    faltantes = serializers.SerializerMethodField()

    class Meta:
        model = PrestamoPaquete
        fields = ["id", "nombre", "tarifa_diaria_aplicada", "tarifa_mensual_aplicada", "faltantes"]

    def get_faltantes(self, obj):
        from apps.activos.models import CategoriaActivo

        faltan = obj.faltantes_por_categoria()
        nombres = dict(CategoriaActivo.objects.filter(pk__in=faltan).values_list("pk", "nombre"))
        return [{"categoria_id": k, "categoria": nombres[k], "cantidad": v} for k, v in faltan.items()]


class FirmaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Firma
        fields = ["tipo", "nombre_firmante", "rut_firmante", "imagen", "fecha", "hash"]


class PrestamoSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source="contratista.razon_social", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    paquetes = PrestamoPaqueteSerializer(many=True, read_only=True)
    detalles = DetalleSerializer(many=True, read_only=True)
    firmas = FirmaSerializer(many=True, read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Prestamo
        fields = [
            "id", "codigo", "contratista", "contratista_nombre", "obra", "obra_nombre", "fecha_entrega",
            "fecha_devolucion_pactada", "fecha_devolucion_real", "estado", "estado_display", "observaciones",
            "paquetes", "detalles", "firmas", "url",
        ]


class PrestamoListaSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source="contratista.razon_social", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Prestamo
        fields = [
            "id", "codigo", "contratista_nombre", "obra_nombre", "fecha_entrega", "fecha_devolucion_pactada",
            "fecha_devolucion_real", "estado", "estado_display", "url",
        ]


class PrestamoEntradaSerializer(serializers.Serializer):
    """Entrada para cotizar y crear un préstamo."""

    contratista = serializers.PrimaryKeyRelatedField(queryset=Contratista.objects.all(), required=False)
    obra = serializers.PrimaryKeyRelatedField(queryset=Obra.objects.all(), required=False)
    fecha_entrega = serializers.DateField()
    fecha_devolucion_pactada = serializers.DateField()
    paquetes = serializers.PrimaryKeyRelatedField(queryset=PaqueteMaquinaria.objects.filter(activo=True), many=True, required=False)
    activos = serializers.PrimaryKeyRelatedField(queryset=Activo.objects.select_related("categoria"), many=True, required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class FirmaEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    rut = serializers.CharField(max_length=12)
    imagen = serializers.CharField()


class CobroSerializer(serializers.ModelSerializer):
    prestamo_codigo = serializers.CharField(source="prestamo.codigo", read_only=True)
    contratista = serializers.CharField(source="prestamo.contratista.razon_social", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Cobro
        fields = [
            "id", "prestamo", "prestamo_codigo", "contratista", "dias_cobrados", "dias_atraso", "monto_arriendo",
            "monto_atraso", "monto_danos", "neto", "iva", "total", "estado", "estado_display", "creado", "fecha_pago",
        ]
        read_only_fields = fields
