from . import roles


def rol(request):
    usuario = getattr(request, "user", None)
    actual = roles.rol_de(usuario)
    datos = {
        "rol": actual,
        "rol_clave": roles.CLAVES.get(actual, ""),
        "es_admin": actual == roles.ADMIN,
        "es_bodeguero": actual == roles.BODEGUERO,
        "es_encargado": actual == roles.ENCARGADO,
        "es_ventas": actual == roles.VENTAS,
        "alertas_abiertas": 0,
    }
    if actual:
        from apps.alertas.services import alertas_para

        datos["alertas_abiertas"] = alertas_para(usuario).filter(resuelta=False, leida=False).count()
    return datos
