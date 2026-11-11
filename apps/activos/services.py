"""Lógica de negocio de activos. Los estados solo cambian desde aquí."""
import io

import qrcode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Activo, CategoriaActivo, HistorialEstado, Traslado

E = Activo.Estado

TRANSICIONES = {
    E.DISPONIBLE: {E.EN_USO, E.MANTENIMIENTO, E.DADO_DE_BAJA},
    E.EN_USO: {E.DISPONIBLE, E.MANTENIMIENTO},
    E.MANTENIMIENTO: {E.DISPONIBLE, E.DADO_DE_BAJA},
    E.DADO_DE_BAJA: set(),
}


@transaction.atomic
def crear_activo(usuario, **datos):
    """Crea el activo con su código correlativo (RTM-0004) y su plan de mantención."""
    from apps.mantenimiento.models import PlanMantenimiento

    categoria = CategoriaActivo.objects.select_for_update().get(pk=datos.pop("categoria").pk)
    categoria.ultimo_correlativo += 1
    categoria.save(update_fields=["ultimo_correlativo"])
    activo = Activo.objects.create(
        categoria=categoria, codigo=f"{categoria.prefijo_codigo}-{categoria.ultimo_correlativo:04d}", **datos
    )
    PlanMantenimiento.objects.create(
        activo=activo,
        cada_usos=categoria.mant_cada_usos,
        cada_horas=categoria.mant_cada_horas,
        cada_dias=categoria.mant_cada_dias,
    )
    HistorialEstado.objects.create(
        activo=activo, estado_nuevo=activo.estado, usuario=usuario, motivo="Alta del activo"
    )
    return activo


def cambiar_estado(activo, nuevo, usuario, motivo="", referencia=""):
    """Único punto donde cambia `Activo.estado`. Deja registro en la hoja de vida."""
    if nuevo == activo.estado:
        return activo
    if nuevo not in TRANSICIONES[activo.estado]:
        raise ValidationError(
            f"{activo.codigo}: no se puede pasar de {activo.get_estado_display()} a {E(nuevo).label}."
        )
    anterior = activo.estado
    activo.estado = nuevo
    activo.save(update_fields=["estado"])
    HistorialEstado.objects.create(
        activo=activo, estado_anterior=anterior, estado_nuevo=nuevo,
        usuario=usuario, motivo=motivo, referencia=referencia,
    )
    return activo


def validar_entregable(activo):
    """Un activo se entrega solo si está DISPONIBLE y su mantención no está vencida."""
    if activo.estado != E.DISPONIBLE:
        raise ValidationError(f"{activo.codigo} no está disponible ({activo.get_estado_display()}).")
    plan = getattr(activo, "plan", None)
    if plan and plan.vencido:
        raise ValidationError(f"{activo.codigo} tiene la mantención vencida y no se puede entregar.")


@transaction.atomic
def enviar_a_mantenimiento(activo, usuario, motivo):
    from apps.alertas.models import Alerta
    from apps.alertas.services import crear_alerta
    from apps.usuarios.roles import BODEGUERO

    cambiar_estado(activo, E.MANTENIMIENTO, usuario, motivo)
    crear_alerta(
        Alerta.Tipo.MANTENCION_VENCIDA, f"{activo.codigo} en mantenimiento: {motivo}",
        objeto=activo, nivel=Alerta.Nivel.WARNING, rol_destino=BODEGUERO,
    )
    return activo


@transaction.atomic
def dar_de_baja(activo, usuario, motivo):
    if not motivo:
        raise ValidationError("Indica el motivo de la baja.")
    cambiar_estado(activo, E.DADO_DE_BAJA, usuario, motivo)
    activo.activo = False
    activo.save(update_fields=["activo"])
    return activo


@transaction.atomic
def trasladar(activo, destino, usuario, observacion=""):
    if activo.estado == E.EN_USO:
        raise ValidationError(f"{activo.codigo} está en terreno; se traslada al devolverlo.")
    if activo.estado == E.DADO_DE_BAJA:
        raise ValidationError(f"{activo.codigo} está dado de baja.")
    if activo.bodega_actual_id == destino.pk:
        raise ValidationError(f"{activo.codigo} ya está en {destino}.")
    traslado = Traslado.objects.create(
        activo=activo, bodega_origen=activo.bodega_actual, bodega_destino=destino,
        usuario=usuario, observacion=observacion,
    )
    activo.bodega_actual = destino
    activo.save(update_fields=["bodega_actual"])
    return traslado


def url_absoluta(objeto, request=None):
    """URL completa de `objeto.get_absolute_url()`; usa SITE_URL si está definida."""
    ruta = objeto.get_absolute_url()
    if settings.SITE_URL:
        return settings.SITE_URL.rstrip("/") + ruta
    return request.build_absolute_uri(ruta) if request else ruta


url_ficha = url_absoluta


def qr_png(objeto, request=None):
    """PNG del QR con la URL del objeto (ficha de un activo o detalle de un préstamo).
    Se genera al vuelo: si cambia la IP de la EC2, basta con reimprimir las etiquetas."""
    img = qrcode.make(url_absoluta(objeto, request), box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def disponibles_por_categoria():
    """{categoria_id: cantidad entregable ahora}."""
    conteo = {}
    for a in Activo.objects.filter(estado=E.DISPONIBLE, activo=True).select_related("plan"):
        plan = getattr(a, "plan", None)
        if plan and plan.vencido:
            continue
        conteo[a.categoria_id] = conteo.get(a.categoria_id, 0) + 1
    return conteo


def disponibilidad_paquete(paquete, conteo=None):
    conteo = conteo if conteo is not None else disponibles_por_categoria()
    items = []
    for item in paquete.items.select_related("categoria"):
        hay = conteo.get(item.categoria_id, 0)
        items.append({
            "categoria": item.categoria.nombre,
            "categoria_id": item.categoria_id,
            "requeridos": item.cantidad,
            "disponibles": hay,
            "alcanza": hay >= item.cantidad,
        })
    return {"disponible": all(i["alcanza"] for i in items), "items": items}
