from django.conf import settings
from django.db import models
from django.urls import reverse


class CategoriaActivo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    prefijo_codigo = models.CharField("prefijo de código", max_length=4, unique=True, help_text="Ej.: RTM")
    descripcion = models.TextField("descripción", blank=True)
    tarifa_diaria = models.PositiveIntegerField("tarifa diaria (CLP)")
    tarifa_mensual = models.PositiveIntegerField("tarifa mensual (CLP)")
    requiere_horometro = models.BooleanField("requiere horómetro", default=False)
    mant_cada_usos = models.PositiveIntegerField("mantención cada N usos", null=True, blank=True)
    mant_cada_horas = models.PositiveIntegerField("mantención cada N horas", null=True, blank=True)
    mant_cada_dias = models.PositiveIntegerField("mantención cada N días", null=True, blank=True)
    ultimo_correlativo = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría de activo"
        verbose_name_plural = "categorías de activo"

    def __str__(self):
        return f"{self.nombre} ({self.prefijo_codigo})"


class Bodega(models.Model):
    class Tipo(models.TextChoices):
        CENTRAL = "CENTRAL", "Central"
        OBRA = "OBRA", "Bodega de obra"

    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.CENTRAL)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    obra = models.ForeignKey(
        "contratistas.Obra", null=True, blank=True, on_delete=models.SET_NULL, related_name="bodegas"
    )
    encargado = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bodegas"
    )

    class Meta:
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return self.nombre


class Activo(models.Model):
    class Estado(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        EN_USO = "EN_USO", "En uso"
        MANTENIMIENTO = "MANTENIMIENTO", "Mantenimiento"
        DADO_DE_BAJA = "DADO_DE_BAJA", "Dado de baja"

    codigo = models.CharField("código", max_length=12, unique=True, editable=False)
    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        CategoriaActivo, on_delete=models.PROTECT, related_name="activos", verbose_name="categoría"
    )
    marca = models.CharField(max_length=60, blank=True)
    modelo = models.CharField(max_length=60, blank=True)
    numero_serie = models.CharField("número de serie", max_length=60, blank=True)
    fecha_adquisicion = models.DateField("fecha de adquisición", null=True, blank=True)
    valor_compra = models.PositiveIntegerField("valor de compra (CLP)", null=True, blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.DISPONIBLE, editable=False)
    bodega_actual = models.ForeignKey(
        Bodega, null=True, blank=True, on_delete=models.SET_NULL, related_name="activos", verbose_name="bodega"
    )
    horas_uso_totales = models.DecimalField("horas de uso", max_digits=9, decimal_places=1, default=0, editable=False)
    usos_totales = models.PositiveIntegerField(default=0, editable=False)
    usos_desde_mantencion = models.PositiveIntegerField("usos desde la mantención", default=0, editable=False)
    foto = models.ImageField(upload_to="activos/", null=True, blank=True)
    activo = models.BooleanField(default=True, help_text="Desmarcar para ocultarlo sin borrar su historia.")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    def get_absolute_url(self):
        return reverse("activos:ficha", args=[self.codigo])


class HistorialEstado(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=15, blank=True)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255, blank=True)
    referencia = models.CharField(max_length=40, blank=True, help_text="Folio de préstamo o mantención")

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "historial de estado"
        verbose_name_plural = "historial de estados"


class Traslado(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="traslados")
    bodega_origen = models.ForeignKey(Bodega, null=True, on_delete=models.SET_NULL, related_name="+")
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField("observación", max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha"]


class PaqueteMaquinaria(models.Model):
    codigo = models.CharField("código", max_length=12, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    tarifa_diaria = models.PositiveIntegerField("tarifa diaria (CLP)")
    tarifa_mensual = models.PositiveIntegerField("tarifa mensual (CLP)")
    activo = models.BooleanField("disponible para arriendo", default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "paquete de maquinaria"
        verbose_name_plural = "paquetes de maquinaria"

    def __str__(self):
        return self.nombre

    @property
    def tarifa_diaria_individual(self):
        """Suma de las tarifas diarias sueltas, para mostrar el descuento del paquete."""
        return sum(i.categoria.tarifa_diaria * i.cantidad for i in self.items.all())


class ItemPaquete(models.Model):
    paquete = models.ForeignKey(PaqueteMaquinaria, on_delete=models.CASCADE, related_name="items")
    categoria = models.ForeignKey(CategoriaActivo, on_delete=models.PROTECT, verbose_name="categoría")
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("paquete", "categoria")
        verbose_name = "ítem de paquete"
        verbose_name_plural = "ítems de paquete"

    def __str__(self):
        return f"{self.cantidad} × {self.categoria.nombre}"
