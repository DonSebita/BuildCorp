from django.db import transaction
from django.utils import timezone

from apps.activos.models import Activo
from apps.activos.services import cambiar_estado
from apps.alertas.models import Alerta
from apps.alertas.services import crear_alerta, resolver_alertas
from apps.usuarios.roles import BODEGUERO

from .models import Mantenimiento, PlanMantenimiento


def siguiente_folio(anio=None):
    anio = anio or timezone.localdate().year
    prefijo = f"MNT-{anio}-"
    ultimo = (
        Mantenimiento.objects.select_for_update()
        .filter(folio__startswith=prefijo).order_by("-folio").values_list("folio", flat=True).first()
    )
    n = int(ultimo.rsplit("-", 1)[1]) + 1 if ultimo else 1
    return f"{prefijo}{n:04d}"


@transaction.atomic
def registrar_mantenimiento(activo, usuario, **datos):
    """Registra la mantención con folio propio. Si queda FINALIZADA reinicia los
    contadores del plan y devuelve el activo a DISPONIBLE."""
    mant = Mantenimiento(activo=activo, registrado_por=usuario, **datos)
    mant.folio = siguiente_folio(mant.fecha.year)
    if mant.horas_al_momento is None:
        mant.horas_al_momento = activo.horas_uso_totales
    mant.save()

    if activo.estado == Activo.Estado.DISPONIBLE:
        cambiar_estado(activo, Activo.Estado.MANTENIMIENTO, usuario, f"Ingreso a mantención {mant.folio}", mant.folio)

    if mant.estado == Mantenimiento.Estado.FINALIZADA:
        finalizar(mant, usuario)
    return mant


@transaction.atomic
def finalizar(mant, usuario):
    activo = mant.activo
    mant.estado = Mantenimiento.Estado.FINALIZADA
    mant.save(update_fields=["estado"])
    plan, _ = PlanMantenimiento.objects.get_or_create(activo=activo)
    plan.ultima_fecha = mant.fecha
    plan.ultimas_horas = activo.horas_uso_totales
    plan.save(update_fields=["ultima_fecha", "ultimas_horas"])
    activo.usos_desde_mantencion = 0
    activo.save(update_fields=["usos_desde_mantencion"])
    if activo.estado == Activo.Estado.MANTENIMIENTO:
        cambiar_estado(activo, Activo.Estado.DISPONIBLE, usuario, f"Mantención {mant.folio} finalizada", mant.folio)
    resolver_alertas(activo, Alerta.Tipo.MANTENCION_PROXIMA, Alerta.Tipo.MANTENCION_VENCIDA, Alerta.Tipo.DANO)
    return mant


def revisar_plan(activo, usuario=None):
    """Revisa el plan de un activo y crea alertas. Devuelve 'VENCIDO', 'PROXIMO' o 'AL_DIA'.

    - En bodega y vencido: pasa a MANTENIMIENTO.
    - En terreno y vencido: alerta para recuperarlo al devolverlo.
    """
    plan = getattr(activo, "plan", None)
    if plan is None:
        return "AL_DIA"
    situacion = plan.situacion
    if situacion == "VENCIDO":
        if activo.estado == Activo.Estado.DISPONIBLE:
            cambiar_estado(activo, Activo.Estado.MANTENIMIENTO, usuario, f"Mantención preventiva vencida ({plan.criterio})")
            mensaje = f"{activo.codigo} pasó a mantenimiento: plan vencido ({plan.criterio})"
        elif activo.estado == Activo.Estado.EN_USO:
            mensaje = f"{activo.codigo} tiene la mantención vencida; envíalo a taller al devolverlo"
        else:
            mensaje = f"{activo.codigo} con mantención vencida"
        crear_alerta(Alerta.Tipo.MANTENCION_VENCIDA, mensaje, objeto=activo,
                     nivel=Alerta.Nivel.CRITICO, rol_destino=BODEGUERO)
    elif situacion == "PROXIMO" and activo.estado != Activo.Estado.MANTENIMIENTO:
        crear_alerta(Alerta.Tipo.MANTENCION_PROXIMA, f"{activo.codigo}: mantención próxima ({plan.criterio})",
                     objeto=activo, nivel=Alerta.Nivel.INFO, rol_destino=BODEGUERO)
    return situacion


def revisar_mantenimientos():
    """Tarea diaria (cron). Devuelve el resumen de lo revisado."""
    resumen = {"VENCIDO": 0, "PROXIMO": 0, "AL_DIA": 0}
    activos = Activo.objects.filter(activo=True).exclude(estado=Activo.Estado.DADO_DE_BAJA).select_related("plan")
    for activo in activos:
        with transaction.atomic():
            resumen[revisar_plan(activo)] += 1
    return resumen
