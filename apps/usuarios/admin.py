from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "rol", "rut", "cargo", "is_active", "last_login")
    list_filter = ("groups", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "rut", "email")
    fieldsets = UserAdmin.fieldsets + (("Datos BuildCorp", {"fields": ("rut", "telefono", "cargo")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos BuildCorp", {"fields": ("first_name", "last_name", "rut", "cargo", "groups")}),
    )

    @admin.display(description="Rol")
    def rol(self, obj):
        return obj.rol or "—"
