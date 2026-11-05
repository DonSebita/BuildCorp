from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Alerta(models.Model):
    class Tipo(models.TextChoices):
        MOROSIDAD = "MOROSIDAD", "Morosidad"
        BLOQUEO = "BLOQUEO", "Contratista bloqueado"
        MANTENCION_PROXIMA = "MANTENCION_PROXIMA", "Mantención próxima"
        MANTENCION_VENCIDA = "MANTENCION_VENCIDA", "Mantención vencida"
        DANO = "DANO", "Daño o faltante"
        SOLICITUD_DESBLOQUEO = "SOLICITUD_DESBLOQUEO", "Solicitud de desbloqueo"
        SOLICITUD_BAJA = "SOLICITUD_BAJA", "Solicitud de baja"

    class Nivel(models.TextChoices):
        INFO = "INFO", "Aviso"
        WARNING = "WARNING", "Atención"
        CRITICO = "CRITICO", "Crítico"

    tipo = models.CharField(max_length=22, choices=Tipo.choices)
    nivel = models.CharField(max_length=8, choices=Nivel.choices, default=Nivel.INFO)
    mensaje = models.CharField(max_length=255)
    rol_destino = models.CharField(
        max_length=20, blank=True, help_text="Rol que debe atenderla. Vacío = todos. El Admin ve todas."
    )
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    objeto = GenericForeignKey("content_type", "object_id")
    leida = models.BooleanField(default=False)
    resuelta = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resuelta", "-fecha"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return self.mensaje

    @property
    def enlace(self):
        obj = self.objeto
        return obj.get_absolute_url() if obj is not None and hasattr(obj, "get_absolute_url") else ""
