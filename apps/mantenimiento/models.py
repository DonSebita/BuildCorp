from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PlanMantenimiento(models.Model):
    """Plan preventivo de un activo. Gana el criterio que ocurra primero."""

    activo = models.OneToOneField("activos.Activo", on_delete=models.CASCADE, related_name="plan")
    cada_usos = models.PositiveIntegerField(null=True, blank=True)
    cada_horas = models.PositiveIntegerField(null=True, blank=True)
    cada_dias = models.PositiveIntegerField(null=True, blank=True)
    ultima_fecha = models.DateField("última mantención", default=timezone.localdate)
    ultimas_horas = models.DecimalField("horas en la última mantención", max_digits=9, decimal_places=1, default=0)

    class Meta:
        verbose_name = "plan de mantenimiento"
        verbose_name_plural = "planes de mantenimiento"

    def __str__(self):
        return f"Plan {self.activo.codigo}"

    @property
    def usos_restantes(self):
        if not self.cada_usos:
            return None
        return self.cada_usos - self.activo.usos_desde_mantencion

    @property
    def horas_restantes(self):
        if not self.cada_horas:
            return None
        return float(self.cada_horas) - float(self.activo.horas_uso_totales - self.ultimas_horas)

    @property
    def horas_desde_mantencion(self):
        return float(self.activo.horas_uso_totales - self.ultimas_horas)

    @property
    def proxima_fecha(self):
        if not self.cada_dias:
            return None
        return self.ultima_fecha + timedelta(days=self.cada_dias)

    @property
    def dias_restantes(self):
        if not self.cada_dias:
            return None
        return (self.proxima_fecha - timezone.localdate()).days

    @property
    def vencido(self):
        return any(
            v is not None and v <= 0 for v in (self.usos_restantes, self.horas_restantes, self.dias_restantes)
        )

    @property
    def proxima(self):
        """Alerta temprana: ≤2 usos, ≤10 % de las horas o ≤7 días."""
        if self.vencido:
            return False
        u, h, d = self.usos_restantes, self.horas_restantes, self.dias_restantes
        return (
            (u is not None and u <= 2)
            or (h is not None and h <= self.cada_horas * 0.1)
            or (d is not None and d <= 7)
        )

    @property
    def situacion(self):
        if self.vencido:
            return "VENCIDO"
        if self.proxima:
            return "PROXIMO"
        return "AL_DIA"

    @property
    def criterio(self):
        """Texto del criterio más cercano, para mostrar en listas: «quedan 2 usos», «40 h de exceso»."""
        def texto(valor, singular, plural):
            n = abs(round(valor))
            unidad = singular if n == 1 else plural
            if valor > 0:
                return f"quedan {n} {unidad}"
            return "llegó al límite" if n == 0 else f"{n} {unidad} de exceso"

        partes = []
        if self.usos_restantes is not None:
            partes.append((self.usos_restantes / self.cada_usos, texto(self.usos_restantes, "uso", "usos")))
        if self.horas_restantes is not None:
            partes.append((self.horas_restantes / self.cada_horas, texto(self.horas_restantes, "hora", "horas")))
        if self.dias_restantes is not None:
            partes.append((self.dias_restantes / self.cada_dias, texto(self.dias_restantes, "día", "días")))
        if not partes:
            return "Sin plan"
        return min(partes)[1]


class Mantenimiento(models.Model):
    class Tipo(models.TextChoices):
        PREVENTIVO = "PREVENTIVO", "Preventivo"
        CORRECTIVO = "CORRECTIVO", "Correctivo"

    class Estado(models.TextChoices):
        EN_CURSO = "EN_CURSO", "En curso"
        FINALIZADA = "FINALIZADA", "Finalizada"

    folio = models.CharField(max_length=14, unique=True, editable=False)
    activo = models.ForeignKey("activos.Activo", on_delete=models.PROTECT, related_name="mantenimientos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.PREVENTIVO)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.FINALIZADA)
    fecha = models.DateField(default=timezone.localdate)
    horas_al_momento = models.DecimalField(max_digits=9, decimal_places=1, null=True, blank=True)
    tecnico = models.CharField("técnico", max_length=100)
    costo = models.PositiveIntegerField("costo (CLP)", default=0)
    descripcion = models.TextField("descripción del trabajo")
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "mantención"
        verbose_name_plural = "mantenciones"

    def __str__(self):
        return self.folio
