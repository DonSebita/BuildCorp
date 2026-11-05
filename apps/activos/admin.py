import csv

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.html import format_html

from apps.mantenimiento.models import Mantenimiento, PlanMantenimiento

from . import services
from .models import Activo, Bodega, CategoriaActivo, HistorialEstado, ItemPaquete, PaqueteMaquinaria, Traslado

COLORES = {
    "DISPONIBLE": "#2D6A3E", "EN_USO": "#2E2A6E", "MANTENIMIENTO": "#8A6200", "DADO_DE_BAJA": "#6E6C85",
    "ACTIVO": "#2D6A3E", "BLOQUEADO": "#C8102E", "BORRADOR": "#2E2A6E", "ENTREGADO": "#2E2A6E",
    "ATRASADO": "#C8102E", "DEVUELTO": "#2D6A3E", "CERRADO": "#6E6C85", "PENDIENTE": "#8A6200", "PAGADO": "#2D6A3E",
    "CRITICO": "#C8102E", "WARNING": "#8A6200", "INFO": "#2E2A6E", "EN_CURSO": "#8A6200", "FINALIZADA": "#2D6A3E",
}


def badge(estado, texto):
    color = COLORES.get(estado, "#2E2A6E")
    return format_html(
        '<span style="border:1.5px solid {0};color:{0};padding:1px 7px;border-radius:4px;'
        'font-weight:700;font-size:11px;letter-spacing:.04em;text-transform:uppercase">{1}</span>',
        color, texto,
    )


def exportar_csv(modeladmin, request, queryset):
    campos = [f.name for f in queryset.model._meta.fields]
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{queryset.model._meta.model_name}.csv"'
    resp.write("﻿")
    w = csv.writer(resp, delimiter=";")
    w.writerow(campos)
    for obj in queryset:
        w.writerow([getattr(obj, c) for c in campos])
    return resp


exportar_csv.short_description = "Exportar CSV"


class HistorialInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    can_delete = False
    readonly_fields = ("fecha", "estado_anterior", "estado_nuevo", "usuario", "motivo", "referencia")

    def has_add_permission(self, request, obj=None):
        return False


class MantenimientoInline(admin.TabularInline):
    model = Mantenimiento
    extra = 0
    can_delete = False
    readonly_fields = ("folio", "fecha", "tipo", "estado", "tecnico", "costo", "descripcion")

    def has_add_permission(self, request, obj=None):
        return False


class PlanInline(admin.StackedInline):
    model = PlanMantenimiento
    can_delete = False
    fields = ("cada_usos", "cada_horas", "cada_dias", "ultima_fecha", "ultimas_horas")


@admin.register(CategoriaActivo)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "prefijo_codigo", "tarifa_diaria", "tarifa_mensual", "requiere_horometro",
                    "mant_cada_usos", "mant_cada_horas", "mant_cada_dias")
    list_filter = ("requiere_horometro",)
    search_fields = ("nombre", "prefijo_codigo")


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "obra", "encargado", "direccion")
    list_filter = ("tipo",)
    search_fields = ("nombre", "direccion")


@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "estado_badge", "bodega_actual", "usos_desde_mantencion",
                    "horas_uso_totales", "activo")
    list_filter = ("estado", "categoria", "bodega_actual", "activo")
    search_fields = ("codigo", "nombre", "numero_serie", "marca", "modelo")
    date_hierarchy = "creado"
    readonly_fields = ("codigo", "estado", "horas_uso_totales", "usos_totales", "usos_desde_mantencion", "creado")
    inlines = [PlanInline, HistorialInline, MantenimientoInline]
    actions = ["enviar_a_mantenimiento", "dar_de_baja", exportar_csv]

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return badge(obj.estado, obj.get_estado_display())

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        datos = {f: form.cleaned_data.get(f) for f in form.cleaned_data}
        nuevo = services.crear_activo(request.user, **datos)
        obj.pk, obj.codigo = nuevo.pk, nuevo.codigo

    @admin.action(description="Enviar a mantenimiento")
    def enviar_a_mantenimiento(self, request, queryset):
        self._masivo(request, queryset, lambda a: services.enviar_a_mantenimiento(a, request.user, "Acción masiva del admin"))

    @admin.action(description="Dar de baja")
    def dar_de_baja(self, request, queryset):
        self._masivo(request, queryset, lambda a: services.dar_de_baja(a, request.user, "Baja masiva desde el admin"))

    def _masivo(self, request, queryset, fn):
        ok = 0
        for activo in queryset:
            try:
                fn(activo)
                ok += 1
            except ValidationError as e:
                self.message_user(request, " ".join(e.messages), messages.WARNING)
        self.message_user(request, f"{ok} activo(s) actualizados.")


@admin.register(HistorialEstado)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("fecha", "activo", "estado_anterior", "estado_nuevo", "usuario", "motivo", "referencia")
    list_filter = ("estado_nuevo",)
    search_fields = ("activo__codigo", "motivo", "referencia")
    date_hierarchy = "fecha"
    readonly_fields = [f.name for f in HistorialEstado._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Traslado)
class TrasladoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "activo", "bodega_origen", "bodega_destino", "usuario")
    list_filter = ("bodega_destino",)
    search_fields = ("activo__codigo",)
    date_hierarchy = "fecha"


class ItemInline(admin.TabularInline):
    model = ItemPaquete
    extra = 1


@admin.register(PaqueteMaquinaria)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tarifa_diaria", "tarifa_mensual", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    inlines = [ItemInline]
