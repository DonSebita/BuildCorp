from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.activos.admin import badge, exportar_csv

from . import services
from .models import Contratista, Obra


class ObraInline(admin.TabularInline):
    model = Obra
    extra = 0
    fields = ("nombre", "responsable_nombre", "responsable_rut", "fecha_inicio", "fecha_fin", "activa")


@admin.register(Contratista)
class ContratistaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "contacto", "telefono", "estado_badge", "fecha_bloqueo")
    list_filter = ("estado",)
    search_fields = ("razon_social", "rut", "contacto", "email")
    readonly_fields = ("estado", "fecha_bloqueo", "motivo_bloqueo", "desbloqueado_por", "fecha_desbloqueo",
                       "motivo_desbloqueo")
    inlines = [ObraInline]
    actions = ["desbloquear", exportar_csv]

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        return badge(obj.estado, obj.get_estado_display())

    @admin.action(description="Desbloquear contratista")
    def desbloquear(self, request, queryset):
        for c in queryset:
            try:
                services.desbloquear(c, request.user, "Desbloqueo desde Django Admin")
                self.message_user(request, f"{c} desbloqueado.")
            except ValidationError as e:
                self.message_user(request, f"{c}: {' '.join(e.messages)}", messages.WARNING)


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "contratista", "responsable_nombre", "fecha_inicio", "fecha_fin", "activa")
    list_filter = ("activa", "contratista")
    search_fields = ("nombre", "responsable_nombre", "contratista__razon_social")
    date_hierarchy = "fecha_inicio"
