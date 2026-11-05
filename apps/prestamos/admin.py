from django.contrib import admin
from django.utils.html import format_html

from apps.activos.admin import badge, exportar_csv

from .models import Cobro, DetallePrestamo, Firma, ParametroSistema, Prestamo, PrestamoPaquete


class PaqueteInline(admin.TabularInline):
    model = PrestamoPaquete
    extra = 0
    readonly_fields = ("paquete", "tarifa_diaria_aplicada", "tarifa_mensual_aplicada")


class DetalleInline(admin.TabularInline):
    model = DetallePrestamo
    extra = 0
    fields = ("activo", "prestamo_paquete", "estado_salida", "horometro_salida", "estado_llegada",
              "horometro_llegada", "observacion_dano", "cargo_dano")
    readonly_fields = fields


class FirmaInline(admin.TabularInline):
    model = Firma
    extra = 0
    can_delete = False
    fields = ("tipo", "nombre_firmante", "rut_firmante", "vista_previa", "fecha", "ip", "hash")
    readonly_fields = fields

    @admin.display(description="Firma")
    def vista_previa(self, obj):
        return format_html('<img src="{}" style="height:60px;background:#fff;border:1px solid #ddd">', obj.imagen.url)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "contratista", "obra", "fecha_entrega", "fecha_devolucion_pactada",
                    "fecha_devolucion_real", "estado_badge")
    list_filter = ("estado", "contratista")
    search_fields = ("codigo", "contratista__razon_social", "obra__nombre")
    date_hierarchy = "fecha_entrega"
    readonly_fields = ("codigo", "estado", "creado_por", "entregado_por", "recibido_por", "creado")
    inlines = [PaqueteInline, DetalleInline, FirmaInline]
    actions = [exportar_csv]

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return badge(obj.estado, obj.get_estado_display())


@admin.register(Firma)
class FirmaAdmin(admin.ModelAdmin):
    list_display = ("prestamo", "tipo", "nombre_firmante", "rut_firmante", "fecha", "ip")
    list_filter = ("tipo",)
    search_fields = ("prestamo__codigo", "nombre_firmante", "rut_firmante")
    date_hierarchy = "fecha"
    readonly_fields = ("prestamo", "tipo", "nombre_firmante", "rut_firmante", "vista_previa", "fecha", "ip", "hash")
    exclude = ("imagen",)

    @admin.display(description="Firma")
    def vista_previa(self, obj):
        return format_html('<img src="{}" style="height:120px;background:#fff;border:1px solid #ddd">', obj.imagen.url)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    list_display = ("prestamo", "dias_cobrados", "dias_atraso", "neto", "iva", "total", "estado_badge", "fecha_pago")
    list_filter = ("estado",)
    search_fields = ("prestamo__codigo", "prestamo__contratista__razon_social")
    date_hierarchy = "creado"
    readonly_fields = ("prestamo", "dias_cobrados", "dias_atraso", "monto_arriendo", "monto_atraso", "monto_danos",
                       "neto", "iva", "total")
    actions = [exportar_csv]

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return badge(obj.estado, obj.get_estado_display())


@admin.register(ParametroSistema)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ("__str__", "dias_gracia", "recargo_atraso", "tasa_iva")

    def has_add_permission(self, request):
        return not ParametroSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
