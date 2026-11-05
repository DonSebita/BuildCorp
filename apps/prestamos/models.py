from django.conf import settings
from django.db import models
from django.urls import reverse


class ParametroSistema(models.Model):
    """Parámetros configurables por el Administrador (una sola fila)."""

    dias_gracia = models.PositiveIntegerField("días de gracia antes del bloqueo", default=3)
    recargo_atraso = models.DecimalField(
        "recargo por atraso", max_digits=4, decimal_places=2, default=0.5, help_text="0,5 = +50 % de la tarifa diaria"
    )
    tasa_iva = models.DecimalField("tasa de IVA", max_digits=4, decimal_places=2, default=0.19)

    class Meta:
        verbose_name = "parámetros del sistema"
        verbose_name_plural = "parámetros del sistema"

    def __str__(self):
        return "Parámetros del sistema"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Prestamo(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Por entregar"
        ENTREGADO = "ENTREGADO", "Entregado"
        ATRASADO = "ATRASADO", "Atrasado"
        DEVUELTO = "DEVUELTO", "Devuelto"
        CERRADO = "CERRADO", "Cerrado"

    EN_TERRENO = (Estado.ENTREGADO, Estado.ATRASADO)

    codigo = models.CharField("folio", max_length=14, unique=True, editable=False)
    contratista = models.ForeignKey("contratistas.Contratista", on_delete=models.PROTECT, related_name="prestamos")
    obra = models.ForeignKey("contratistas.Obra", on_delete=models.PROTECT, related_name="prestamos")
    fecha_entrega = models.DateField("fecha de entrega")
    fecha_devolucion_pactada = models.DateField("devolución pactada")
    fecha_devolucion_real = models.DateField("devolución real", null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR, editable=False)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "préstamo"

    def __str__(self):
        return self.codigo

    def get_absolute_url(self):
        return reverse("prestamos:detalle", args=[self.codigo])

    @property
    def en_terreno(self):
        return self.estado in self.EN_TERRENO


class PrestamoPaquete(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="paquetes")
    paquete = models.ForeignKey("activos.PaqueteMaquinaria", on_delete=models.PROTECT)
    tarifa_diaria_aplicada = models.PositiveIntegerField()
    tarifa_mensual_aplicada = models.PositiveIntegerField()

    class Meta:
        verbose_name = "paquete del préstamo"
        verbose_name_plural = "paquetes del préstamo"

    def __str__(self):
        return f"{self.prestamo} · {self.paquete}"

    def faltantes_por_categoria(self):
        """{categoria_id: cantidad que aún falta asignar}."""
        asignados = {}
        for d in self.detalles.select_related("activo"):
            asignados[d.activo.categoria_id] = asignados.get(d.activo.categoria_id, 0) + 1
        return {
            i.categoria_id: i.cantidad - asignados.get(i.categoria_id, 0)
            for i in self.paquete.items.all()
            if i.cantidad - asignados.get(i.categoria_id, 0) > 0
        }


class DetallePrestamo(models.Model):
    class EstadoFisico(models.TextChoices):
        BUENO = "BUENO", "Bueno"
        DESGASTE = "DESGASTE", "Desgaste normal"
        DANADO = "DANADO", "Dañado"
        FALTANTE = "FALTANTE", "Faltante"

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="detalles")
    activo = models.ForeignKey("activos.Activo", on_delete=models.PROTECT, related_name="detalles_prestamo")
    prestamo_paquete = models.ForeignKey(
        PrestamoPaquete, null=True, blank=True, on_delete=models.CASCADE, related_name="detalles"
    )
    tarifa_diaria_aplicada = models.PositiveIntegerField(null=True, blank=True)
    tarifa_mensual_aplicada = models.PositiveIntegerField(null=True, blank=True)
    horometro_salida = models.DecimalField(max_digits=9, decimal_places=1, null=True, blank=True)
    horometro_llegada = models.DecimalField(max_digits=9, decimal_places=1, null=True, blank=True)
    estado_salida = models.CharField(max_length=10, choices=EstadoFisico.choices, blank=True)
    estado_llegada = models.CharField(max_length=10, choices=EstadoFisico.choices, blank=True)
    observacion_dano = models.CharField("observación de daño", max_length=255, blank=True)
    cargo_dano = models.PositiveIntegerField("cargo por daño (CLP)", default=0)

    class Meta:
        unique_together = ("prestamo", "activo")
        verbose_name = "detalle de préstamo"
        verbose_name_plural = "detalles de préstamo"

    def __str__(self):
        return f"{self.prestamo} · {self.activo.codigo}"

    @property
    def es_suelto(self):
        return self.prestamo_paquete_id is None


class Firma(models.Model):
    class Tipo(models.TextChoices):
        ENTREGA = "ENTREGA", "Entrega"
        DEVOLUCION = "DEVOLUCION", "Devolución"

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="firmas")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    nombre_firmante = models.CharField(max_length=100)
    rut_firmante = models.CharField(max_length=12)
    imagen = models.ImageField(upload_to="firmas/%Y/%m/")
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    hash = models.CharField("hash SHA-256", max_length=64)

    class Meta:
        unique_together = ("prestamo", "tipo")

    def __str__(self):
        return f"Firma {self.get_tipo_display().lower()} {self.prestamo}"


class Cobro(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"

    prestamo = models.OneToOneField(Prestamo, on_delete=models.PROTECT, related_name="cobro")
    dias_cobrados = models.PositiveIntegerField()
    dias_atraso = models.PositiveIntegerField(default=0)
    monto_arriendo = models.PositiveBigIntegerField()
    monto_atraso = models.PositiveBigIntegerField(default=0)
    monto_danos = models.PositiveBigIntegerField(default=0)
    neto = models.PositiveBigIntegerField()
    iva = models.PositiveBigIntegerField()
    total = models.PositiveBigIntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    creado = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Cobro {self.prestamo}"
