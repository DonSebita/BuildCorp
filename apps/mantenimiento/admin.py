from django.contrib import admin

from apps.activos.admin import badge, exportar_csv

from .models import Mantenimiento, PlanMantenimiento


@admin.register(PlanMantenimiento)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("activo", "cada_usos", "cada_horas", "cada_dias", "ultima_fecha", "situacion_badge", "criterio")
    search_fields = ("activo__codigo", "activo__nombre")
    date_hierarchy = "ultima_fecha"

    @admin.display(description="Situación")
    def situacion_badge(self, obj):
        texto = {"VENCIDO": "Vencida", "PROXIMO": "Próxima", "AL_DIA": "Al día"}[obj.situacion]
        return badge({"VENCIDO": "CRITICO", "PROXIMO": "WARNING", "AL_DIA": "DISPONIBLE"}[obj.situacion], texto)


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ("folio", "activo", "tipo", "estado_badge", "fecha", "tecnico", "costo", "registrado_por")
    list_filter = ("tipo", "estado")
    search_fields = ("folio", "activo__codigo", "tecnico")
    date_hierarchy = "fecha"
    readonly_fields = ("folio", "registrado_por")
    actions = [exportar_csv]

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return badge(obj.estado, obj.get_estado_display())
