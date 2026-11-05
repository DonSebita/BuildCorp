"""Lógica de negocio de préstamos: cotización, entrega, devolución, cobro y morosidad."""
import base64
import binascii
import hashlib

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.activos.models import Activo
from apps.activos.services import cambiar_estado, disponibilidad_paquete, disponibles_por_categoria, validar_entregable
from apps.alertas.models import Alerta
from apps.alertas.services import crear_alerta, resolver_alertas
from apps.contratistas.services import bloquear
from apps.usuarios.roles import VENTAS

from .models import Cobro, DetallePrestamo, Firma, ParametroSistema, Prestamo, PrestamoPaquete

EF = DetallePrestamo.EstadoFisico


# ---------------------------------------------------------------- cálculo CLP

def dias_entre(desde, hasta):
    """Días cobrables: cualquier fracción cuenta como día, mínimo 1."""
    return max(1, (hasta - desde).days)


def calcular_arriendo(dias, diaria, mensual):
    if dias < 30:
        return dias * diaria
    meses, resto = divmod(dias, 30)
    return meses * mensual + min(resto * diaria, mensual)


def calcular_totales(lineas, dias, dias_atraso=0, danos=0, params=None):
    """`lineas`: lista de (tarifa_diaria, tarifa_mensual). Devuelve el desglose en CLP enteros."""
    params = params or ParametroSistema.actual()
    arriendo = sum(calcular_arriendo(dias, d, m) for d, m in lineas)
    atraso = round(sum(dias_atraso * d * float(params.recargo_atraso) for d, _ in lineas))
    neto = arriendo + atraso + danos
    iva = round(neto * float(params.tasa_iva))
    return {
        "dias": dias, "dias_atraso": dias_atraso, "arriendo": arriendo, "atraso": atraso,
        "danos": danos, "neto": neto, "iva": iva, "total": neto + iva,
    }


def lineas_de(prestamo):
    lineas = [(pp.tarifa_diaria_aplicada, pp.tarifa_mensual_aplicada) for pp in prestamo.paquetes.all()]
    lineas += [
        (d.tarifa_diaria_aplicada, d.tarifa_mensual_aplicada)
        for d in prestamo.detalles.all() if d.prestamo_paquete_id is None
    ]
    return lineas


def cotizar(fecha_entrega, fecha_devolucion_pactada, paquetes=(), activos=()):
    """Cotización sin guardar. `paquetes` y `activos` son querysets o listas de objetos."""
    if fecha_devolucion_pactada < fecha_entrega:
        raise ValidationError("La devolución pactada no puede ser anterior a la entrega.")
    dias = dias_entre(fecha_entrega, fecha_devolucion_pactada)
    detalle = []
    for p in paquetes:
        detalle.append({"tipo": "paquete", "nombre": p.nombre, "codigo": p.codigo,
                        "diaria": p.tarifa_diaria, "mensual": p.tarifa_mensual,
                        "subtotal": calcular_arriendo(dias, p.tarifa_diaria, p.tarifa_mensual)})
    for a in activos:
        c = a.categoria
        detalle.append({"tipo": "activo", "nombre": a.nombre, "codigo": a.codigo,
                        "diaria": c.tarifa_diaria, "mensual": c.tarifa_mensual,
                        "subtotal": calcular_arriendo(dias, c.tarifa_diaria, c.tarifa_mensual)})
    totales = calcular_totales([(x["diaria"], x["mensual"]) for x in detalle], dias)
    return {"lineas": detalle, **totales}


# ---------------------------------------------------------------- creación

def siguiente_codigo(anio=None):
    anio = anio or timezone.localdate().year
    prefijo = f"P-{anio}-"
    ultimo = (
        Prestamo.objects.select_for_update()
        .filter(codigo__startswith=prefijo).order_by("-codigo").values_list("codigo", flat=True).first()
    )
    n = int(ultimo.rsplit("-", 1)[1]) + 1 if ultimo else 1
    return f"{prefijo}{n:04d}"


def validar_contratista(contratista):
    if contratista.bloqueado:
        raise ValidationError(f"{contratista} está bloqueado por morosidad. Solo el Administrador puede desbloquearlo.")


@transaction.atomic
def crear_prestamo(usuario, contratista, obra, fecha_entrega, fecha_devolucion_pactada,
                   paquetes=(), activos=(), observaciones=""):
    validar_contratista(contratista)
    if obra.contratista_id != contratista.pk:
        raise ValidationError("La obra no pertenece al contratista.")
    if not paquetes and not activos:
        raise ValidationError("Agrega al menos un paquete o un activo.")
    if fecha_devolucion_pactada < fecha_entrega:
        raise ValidationError("La devolución pactada no puede ser anterior a la entrega.")

    activos = list(Activo.objects.select_for_update(of=("self",)).filter(pk__in=[a.pk for a in activos]).select_related("categoria", "plan"))
    for a in activos:
        validar_entregable(a)

    # Disponibilidad por categoría descontando los activos sueltos ya elegidos.
    conteo = disponibles_por_categoria()
    for a in activos:
        conteo[a.categoria_id] = conteo.get(a.categoria_id, 0) - 1
    for p in paquetes:
        disp = disponibilidad_paquete(p, conteo)
        if not disp["disponible"]:
            faltan = ", ".join(i["categoria"] for i in disp["items"] if not i["alcanza"])
            raise ValidationError(f"No hay stock para «{p.nombre}»: falta {faltan}.")
        for i in disp["items"]:
            conteo[i["categoria_id"]] -= i["requeridos"]

    prestamo = Prestamo.objects.create(
        codigo=siguiente_codigo(), contratista=contratista, obra=obra, fecha_entrega=fecha_entrega,
        fecha_devolucion_pactada=fecha_devolucion_pactada, creado_por=usuario, observaciones=observaciones,
    )
    for p in paquetes:
        if not p.activo:
            raise ValidationError(f"El paquete «{p.nombre}» no está disponible para arriendo.")
        PrestamoPaquete.objects.create(prestamo=prestamo, paquete=p, tarifa_diaria_aplicada=p.tarifa_diaria,
                                       tarifa_mensual_aplicada=p.tarifa_mensual)
    for a in activos:
        DetallePrestamo.objects.create(prestamo=prestamo, activo=a, tarifa_diaria_aplicada=a.categoria.tarifa_diaria,
                                       tarifa_mensual_aplicada=a.categoria.tarifa_mensual)
    return prestamo


@transaction.atomic
def asignar_activos(prestamo, prestamo_paquete, codigos):
    """El encargado E/R asigna activos concretos a un paquete (p. ej. escaneando QR)."""
    if prestamo.estado != Prestamo.Estado.BORRADOR:
        raise ValidationError("Solo se asignan activos antes de la entrega.")
    faltan = prestamo_paquete.faltantes_por_categoria()
    for codigo in codigos:
        try:
            activo = Activo.objects.select_for_update(of=("self",)).select_related("plan").get(codigo=codigo.strip().upper())
        except Activo.DoesNotExist:
            raise ValidationError(f"No existe el activo {codigo}.")
        if prestamo.detalles.filter(activo=activo).exists():
            raise ValidationError(f"{activo.codigo} ya está en este préstamo.")
        if faltan.get(activo.categoria_id, 0) <= 0:
            raise ValidationError(f"El paquete no pide más {activo.categoria.nombre.lower()}.")
        validar_entregable(activo)
        DetallePrestamo.objects.create(prestamo=prestamo, activo=activo, prestamo_paquete=prestamo_paquete)
        faltan[activo.categoria_id] -= 1
    return prestamo_paquete


@transaction.atomic
def quitar_activo(prestamo, detalle):
    if prestamo.estado != Prestamo.Estado.BORRADOR:
        raise ValidationError("Solo se quitan activos antes de la entrega.")
    if detalle.prestamo_paquete_id is None:
        raise ValidationError("Los activos sueltos los quita Ventas editando el préstamo.")
    detalle.delete()


# ---------------------------------------------------------------- firma

def guardar_firma(prestamo, tipo, nombre, rut, imagen_b64, ip=None):
    if not nombre or not rut:
        raise ValidationError("Falta el nombre o el RUT de quien firma.")
    if not imagen_b64:
        raise ValidationError("Falta la firma.")
    if "," in imagen_b64:
        imagen_b64 = imagen_b64.split(",", 1)[1]
    try:
        contenido = base64.b64decode(imagen_b64, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError("La imagen de la firma no es válida.")
    if not contenido.startswith(b"\x89PNG") or len(contenido) < 200:
        raise ValidationError("La firma está vacía o no es un PNG.")
    momento = timezone.now().isoformat()
    huella = hashlib.sha256(contenido + f"|{prestamo.codigo}|{tipo}|{nombre}|{rut}|{momento}".encode()).hexdigest()
    firma = Firma(prestamo=prestamo, tipo=tipo, nombre_firmante=nombre, rut_firmante=rut, ip=ip, hash=huella)
    firma.imagen.save(f"{prestamo.codigo}-{tipo.lower()}.png", ContentFile(contenido), save=False)
    firma.save()
    return firma


# ---------------------------------------------------------------- entrega

@transaction.atomic
def entregar(prestamo, usuario, checklist, firma, ip=None):
    """`checklist`: {detalle_id: {"estado_salida": "BUENO", "horometro_salida": 120.5}}.
    `firma`: {"nombre", "rut", "imagen"} (imagen en base64)."""
    prestamo = Prestamo.objects.select_for_update().get(pk=prestamo.pk)
    if prestamo.estado != Prestamo.Estado.BORRADOR:
        raise ValidationError(f"{prestamo.codigo} ya fue entregado.")
    validar_contratista(prestamo.contratista)
    for pp in prestamo.paquetes.all():
        if pp.faltantes_por_categoria():
            raise ValidationError(f"Faltan activos por asignar en «{pp.paquete.nombre}».")
    detalles = list(prestamo.detalles.select_related("activo__categoria", "activo__plan"))
    if not detalles:
        raise ValidationError("El préstamo no tiene activos.")
    for d in detalles:
        validar_entregable(d.activo)
        datos = checklist.get(str(d.pk)) or checklist.get(d.pk) or {}
        d.estado_salida = datos.get("estado_salida") or EF.BUENO
        if d.estado_salida in (EF.DANADO, EF.FALTANTE):
            raise ValidationError(f"{d.activo.codigo} no puede salir en estado {EF(d.estado_salida).label.lower()}.")
        horo = datos.get("horometro_salida")
        if d.activo.categoria.requiere_horometro and horo in (None, ""):
            raise ValidationError(f"Anota el horómetro de salida de {d.activo.codigo}.")
        d.horometro_salida = horo if horo not in ("", None) else None
        d.save(update_fields=["estado_salida", "horometro_salida"])
        cambiar_estado(d.activo, Activo.Estado.EN_USO, usuario, f"Entregado a {prestamo.contratista}", prestamo.codigo)

    guardar_firma(prestamo, Firma.Tipo.ENTREGA, firma.get("nombre"), firma.get("rut"), firma.get("imagen"), ip)
    prestamo.estado = Prestamo.Estado.ENTREGADO
    prestamo.fecha_entrega = timezone.localdate()
    prestamo.entregado_por = usuario
    prestamo.save(update_fields=["estado", "fecha_entrega", "entregado_por"])
    return prestamo


# ---------------------------------------------------------------- devolución

@transaction.atomic
def devolver(prestamo, usuario, recepcion, firma, ip=None, fecha=None):
    """`recepcion`: {detalle_id: {"estado_llegada", "horometro_llegada", "observacion_dano", "cargo_dano"}}."""
    from apps.mantenimiento.services import revisar_plan

    prestamo = Prestamo.objects.select_for_update().get(pk=prestamo.pk)
    if not prestamo.en_terreno:
        raise ValidationError(f"{prestamo.codigo} no está en terreno.")
    fecha = fecha or timezone.localdate()
    for d in prestamo.detalles.select_related("activo__categoria", "activo__plan"):
        datos = recepcion.get(str(d.pk)) or recepcion.get(d.pk) or {}
        d.estado_llegada = datos.get("estado_llegada") or EF.BUENO
        d.observacion_dano = (datos.get("observacion_dano") or "").strip()
        d.cargo_dano = int(datos.get("cargo_dano") or 0)
        if d.estado_llegada in (EF.DANADO, EF.FALTANTE) and not d.observacion_dano:
            raise ValidationError(f"Describe el daño o faltante de {d.activo.codigo}.")
        activo = d.activo
        horo = datos.get("horometro_llegada")
        if activo.categoria.requiere_horometro and d.estado_llegada != EF.FALTANTE:
            if horo in (None, ""):
                raise ValidationError(f"Anota el horómetro de llegada de {activo.codigo}.")
            d.horometro_llegada = horo
            horas = float(horo) - float(d.horometro_salida or 0)
            if horas < 0:
                raise ValidationError(f"El horómetro de llegada de {activo.codigo} es menor que el de salida.")
            activo.horas_uso_totales = float(activo.horas_uso_totales) + horas
        d.save()

        activo.usos_totales += 1
        activo.usos_desde_mantencion += 1
        activo.save(update_fields=["usos_totales", "usos_desde_mantencion", "horas_uso_totales"])
        activo.refresh_from_db()

        if d.estado_llegada in (EF.DANADO, EF.FALTANTE):
            cambiar_estado(activo, Activo.Estado.MANTENIMIENTO, usuario,
                           f"{d.get_estado_llegada_display()} en devolución: {d.observacion_dano}", prestamo.codigo)
            crear_alerta(
                Alerta.Tipo.DANO, f"{activo.codigo} {d.get_estado_llegada_display().lower()} en {prestamo.codigo}: {d.observacion_dano}",
                objeto=activo, nivel=Alerta.Nivel.CRITICO if d.estado_llegada == EF.FALTANTE else Alerta.Nivel.WARNING,
            )
        else:
            cambiar_estado(activo, Activo.Estado.DISPONIBLE, usuario, "Devolución conforme", prestamo.codigo)
            revisar_plan(activo, usuario)  # pasa a MANTENIMIENTO si alcanzó su umbral

    guardar_firma(prestamo, Firma.Tipo.DEVOLUCION, firma.get("nombre"), firma.get("rut"), firma.get("imagen"), ip)
    prestamo.estado = Prestamo.Estado.DEVUELTO
    prestamo.fecha_devolucion_real = fecha
    prestamo.recibido_por = usuario
    prestamo.save(update_fields=["estado", "fecha_devolucion_real", "recibido_por"])
    resolver_alertas(prestamo, Alerta.Tipo.MOROSIDAD)
    generar_cobro(prestamo)
    return prestamo


def desglose(prestamo, hasta=None):
    """Cálculo del cobro de un préstamo (devuelto o simulado a la fecha `hasta`)."""
    hasta = hasta or prestamo.fecha_devolucion_real or timezone.localdate()
    dias = dias_entre(prestamo.fecha_entrega, hasta)
    dias_atraso = max(0, (hasta - prestamo.fecha_devolucion_pactada).days)
    danos = sum(d.cargo_dano for d in prestamo.detalles.all())
    return calcular_totales(lineas_de(prestamo), dias, dias_atraso, danos)


def generar_cobro(prestamo):
    t = desglose(prestamo)
    cobro, _ = Cobro.objects.update_or_create(prestamo=prestamo, defaults={
        "dias_cobrados": t["dias"], "dias_atraso": t["dias_atraso"], "monto_arriendo": t["arriendo"],
        "monto_atraso": t["atraso"], "monto_danos": t["danos"], "neto": t["neto"], "iva": t["iva"], "total": t["total"],
    })
    return cobro


@transaction.atomic
def registrar_pago(cobro, usuario, fecha=None):
    if cobro.estado == Cobro.Estado.PAGADO:
        raise ValidationError("Este cobro ya está pagado.")
    cobro.estado = Cobro.Estado.PAGADO
    cobro.fecha_pago = fecha or timezone.localdate()
    cobro.registrado_por = usuario
    cobro.save(update_fields=["estado", "fecha_pago", "registrado_por"])
    prestamo = cobro.prestamo
    prestamo.estado = Prestamo.Estado.CERRADO
    prestamo.save(update_fields=["estado"])
    return cobro


# ---------------------------------------------------------------- morosidad (cron)

def revisar_morosidad(hoy=None):
    """Marca préstamos atrasados, crea alertas y bloquea a quien supere los días de gracia."""
    hoy = hoy or timezone.localdate()
    gracia = ParametroSistema.actual().dias_gracia
    resumen = {"atrasados": 0, "bloqueados": 0}
    vencidos = Prestamo.objects.filter(
        estado__in=Prestamo.EN_TERRENO, fecha_devolucion_pactada__lt=hoy
    ).select_related("contratista")
    for p in vencidos:
        with transaction.atomic():
            dias = (hoy - p.fecha_devolucion_pactada).days
            if p.estado != Prestamo.Estado.ATRASADO:
                p.estado = Prestamo.Estado.ATRASADO
                p.save(update_fields=["estado"])
            resumen["atrasados"] += 1
            nivel = Alerta.Nivel.CRITICO if dias > gracia else Alerta.Nivel.WARNING
            crear_alerta(Alerta.Tipo.MOROSIDAD, f"{p.codigo} de {p.contratista} lleva {dias} día(s) de atraso",
                         objeto=p, nivel=nivel, rol_destino=VENTAS)
            if dias > gracia and not p.contratista.bloqueado:
                bloquear(p.contratista, f"{p.codigo} con {dias} días de atraso (gracia: {gracia})")
                resumen["bloqueados"] += 1
    return resumen
