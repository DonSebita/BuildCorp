from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.alertas.models import Alerta
from apps.alertas.services import crear_alerta, resolver_alertas
from apps.usuarios.roles import ADMIN, VENTAS

from .models import Contratista


@transaction.atomic
def bloquear(contratista, motivo):
    if contratista.bloqueado:
        return contratista
    contratista.estado = Contratista.Estado.BLOQUEADO
    contratista.fecha_bloqueo = timezone.now()
    contratista.motivo_bloqueo = motivo
    contratista.save(update_fields=["estado", "fecha_bloqueo", "motivo_bloqueo"])
    crear_alerta(
        Alerta.Tipo.BLOQUEO, f"{contratista} bloqueado: {motivo}",
        objeto=contratista, nivel=Alerta.Nivel.CRITICO, rol_destino=VENTAS,
    )
    return contratista


@transaction.atomic
def desbloquear(contratista, usuario, motivo):
    """Solo el Administrador desbloquea, y el motivo queda registrado."""
    if not contratista.bloqueado:
        raise ValidationError("El contratista no está bloqueado.")
    if not motivo or len(motivo.strip()) < 5:
        raise ValidationError("Escribe el motivo del desbloqueo (mínimo 5 caracteres).")
    contratista.estado = Contratista.Estado.ACTIVO
    contratista.desbloqueado_por = usuario
    contratista.fecha_desbloqueo = timezone.now()
    contratista.motivo_desbloqueo = motivo.strip()
    contratista.save(update_fields=["estado", "desbloqueado_por", "fecha_desbloqueo", "motivo_desbloqueo"])
    resolver_alertas(contratista, Alerta.Tipo.BLOQUEO, Alerta.Tipo.SOLICITUD_DESBLOQUEO)
    return contratista


def solicitar_desbloqueo(contratista, usuario, motivo):
    if not contratista.bloqueado:
        raise ValidationError("El contratista no está bloqueado.")
    return crear_alerta(
        Alerta.Tipo.SOLICITUD_DESBLOQUEO,
        f"{usuario} solicita desbloquear a {contratista}: {motivo}",
        objeto=contratista, nivel=Alerta.Nivel.WARNING, rol_destino=ADMIN,
    )
