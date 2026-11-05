from django.conf import settings
from django.db import models
from django.urls import reverse


class Contratista(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        BLOQUEADO = "BLOQUEADO", "Bloqueado"

    rut = models.CharField("RUT", max_length=12, unique=True)
    razon_social = models.CharField("razón social", max_length=150)
    contacto = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO, editable=False)
    fecha_bloqueo = models.DateTimeField(null=True, blank=True, editable=False)
    motivo_bloqueo = models.CharField(max_length=255, blank=True, editable=False)
    desbloqueado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, editable=False, related_name="+"
    )
    fecha_desbloqueo = models.DateTimeField(null=True, blank=True, editable=False)
    motivo_desbloqueo = models.CharField(max_length=255, blank=True, editable=False)

    class Meta:
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social

    def get_absolute_url(self):
        return reverse("contratistas:detalle", args=[self.pk])

    @property
    def bloqueado(self):
        return self.estado == self.Estado.BLOQUEADO


class Obra(models.Model):
    nombre = models.CharField(max_length=120)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    contratista = models.ForeignKey(Contratista, on_delete=models.CASCADE, related_name="obras")
    responsable_nombre = models.CharField("responsable de obra", max_length=100)
    responsable_rut = models.CharField("RUT del responsable", max_length=12)
    fecha_inicio = models.DateField("inicio", null=True, blank=True)
    fecha_fin = models.DateField("término", null=True, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
