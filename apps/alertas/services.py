from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from apps.usuarios.roles import ADMIN, rol_de

from .models import Alerta


def crear_alerta(tipo, mensaje, objeto=None, nivel=Alerta.Nivel.WARNING, rol_destino=""):
    """Crea una alerta, sin duplicar una igual que siga abierta para el mismo objeto."""
    filtros = {"tipo": tipo, "resuelta": False}
    if objeto is not None:
        filtros["content_type"] = ContentType.objects.get_for_model(objeto)
        filtros["object_id"] = objeto.pk
    existente = Alerta.objects.filter(**filtros).first()
    if existente:
        if existente.mensaje != mensaje or existente.nivel != nivel:
            existente.mensaje, existente.nivel, existente.leida = mensaje, nivel, False
            existente.save(update_fields=["mensaje", "nivel", "leida"])
        return existente
    return Alerta.objects.create(
        tipo=tipo, mensaje=mensaje, nivel=nivel, rol_destino=rol_destino, **{
            k: v for k, v in filtros.items() if k in ("content_type", "object_id")
        }
    )


def resolver_alertas(objeto, *tipos):
    ct = ContentType.objects.get_for_model(objeto)
    qs = Alerta.objects.filter(content_type=ct, object_id=objeto.pk, resuelta=False)
    if tipos:
        qs = qs.filter(tipo__in=tipos)
    qs.update(resuelta=True, leida=True)


def alertas_para(usuario):
    """Alertas visibles para el rol del usuario (el Admin ve todas)."""
    rol = rol_de(usuario)
    qs = Alerta.objects.all()
    if rol != ADMIN:
        qs = qs.filter(Q(rol_destino="") | Q(rol_destino=rol))
    return qs
