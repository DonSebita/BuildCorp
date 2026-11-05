from django.contrib import admin

from apps.activos.admin import badge

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "nivel_badge", "tipo", "mensaje", "rol_destino", "leida", "resuelta")
    list_filter = ("nivel", "tipo", "resuelta", "leida", "rol_destino")
    search_fields = ("mensaje",)
    date_hierarchy = "fecha"
    actions = ["marcar_resueltas"]

    @admin.display(description="Nivel", ordering="nivel")
    def nivel_badge(self, obj):
        return badge(obj.nivel, obj.get_nivel_display())

    @admin.action(description="Marcar como resueltas")
    def marcar_resueltas(self, request, queryset):
        n = queryset.update(resuelta=True, leida=True)
        self.message_user(request, f"{n} alerta(s) resueltas.")
