"""Permisos por rol para DRF y para las vistas con plantillas.

Cada ViewSet declara qué roles pueden leer y cuáles pueden escribir:

    roles_lectura = TODOS
    roles_escritura = (BODEGUERO,)
    roles_por_accion = {"desbloquear": ()}   # () = solo Administrador

El Administrador siempre tiene acceso.
"""
from django.contrib.auth.mixins import AccessMixin
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .roles import TODOS, tiene_rol


def roles_para(view, request):
    accion = getattr(view, "action", None)
    por_accion = getattr(view, "roles_por_accion", {})
    if accion in por_accion:
        return por_accion[accion]
    if request.method in SAFE_METHODS:
        return getattr(view, "roles_lectura", TODOS)
    return getattr(view, "roles_escritura", ())


class PermisoPorRol(BasePermission):
    message = "Tu rol no tiene permiso para esta acción."

    def has_permission(self, request, view):
        return tiene_rol(request.user, *roles_para(view, request))


class RolRequeridoMixin(AccessMixin):
    """Para vistas con plantilla: `roles = (VENTAS,)`. El Admin siempre pasa."""

    roles = TODOS

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not tiene_rol(request.user, *self.roles):
            self.raise_exception = True
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
