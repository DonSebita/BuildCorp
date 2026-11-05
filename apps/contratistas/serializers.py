from rest_framework import serializers

from .models import Contratista, Obra


class ObraSerializer(serializers.ModelSerializer):
    contratista_nombre = serializers.CharField(source="contratista.razon_social", read_only=True)

    class Meta:
        model = Obra
        fields = "__all__"


class ContratistaSerializer(serializers.ModelSerializer):
    obras = ObraSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Contratista
        fields = [
            "id", "rut", "razon_social", "contacto", "email", "telefono", "estado", "estado_display",
            "fecha_bloqueo", "motivo_bloqueo", "obras",
        ]
        read_only_fields = ["estado", "fecha_bloqueo", "motivo_bloqueo"]
