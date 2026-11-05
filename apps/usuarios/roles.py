"""Roles del sistema. Se implementan como Grupos de Django."""

ADMIN = "Administrador"
BODEGUERO = "Bodeguero"
ENCARGADO = "Encargado E/R"
VENTAS = "Ventas"

TODOS = (ADMIN, BODEGUERO, ENCARGADO, VENTAS)

# Clave corta para CSS y plantillas.
CLAVES = {ADMIN: "admin", BODEGUERO: "bodega", ENCARGADO: "terreno", VENTAS: "ventas"}


def rol_de(usuario):
    if not usuario or not usuario.is_authenticated:
        return None
    if usuario.is_superuser:
        return ADMIN
    nombres = set(usuario.groups.values_list("name", flat=True))
    for rol in TODOS:
        if rol in nombres:
            return rol
    return None


def tiene_rol(usuario, *permitidos):
    rol = rol_de(usuario)
    return rol is not None and (rol == ADMIN or rol in permitidos)
