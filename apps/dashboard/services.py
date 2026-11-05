"""Datos del dashboard según el rol. Cada rol ve lo que tiene que hacer hoy."""
from datetime import timedelta

from django.db.models import Case, Count, Sum, When
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone

from apps.activos.models import Activo, HistorialEstado
from apps.alertas.models import Alerta
from apps.alertas.services import alertas_para
from apps.contratistas.models import Contratista
from apps.mantenimiento.models import PlanMantenimiento
from apps.prestamos.models import Cobro, DetallePrestamo, Prestamo
from apps.usuarios.roles import ADMIN, BODEGUERO, ENCARGADO, VENTAS, rol_de

P = Prestamo.Estado

COLORES_ESTADO = {
    "DISPONIBLE": "#2D6A3E",
    "EN_USO": "#2E2A6E",
    "MANTENIMIENTO": "#B07D10",
    "DADO_DE_BAJA": "#8C8AA3",
}


def kpi(etiqueta, valor, formato="num", critico=False, enlace="", detalle=""):
    return {"etiqueta": etiqueta, "valor": valor, "formato": formato, "critico": bool(critico and valor),
            "enlace": enlace, "detalle": detalle}


def tabla(titulo, columnas, filas, vacio, enlace=""):
    return {"titulo": titulo, "columnas": columnas, "filas": filas, "vacio": vacio, "enlace": enlace}


def fila_prestamo(p, accion=None):
    fila = {
        "folio": {"texto": p.codigo, "url": p.get_absolute_url()},
        "contratista": p.contratista.razon_social,
        "obra": p.obra.nombre,
        "fecha": p.fecha_devolucion_pactada.isoformat(),
        "estado": {"estado": p.estado, "texto": p.get_estado_display()},
    }
    if accion:
        fila["accion"] = accion
    return fila


def grafico_estados():
    conteo = dict(Activo.objects.values_list("estado").annotate(n=Count("id")))
    estados = Activo.Estado
    return {
        "titulo": "Activos por estado",
        "tipo": "bar",
        "etiquetas": [e.label for e in estados],
        "valores": [conteo.get(e.value, 0) for e in estados],
        "colores": [COLORES_ESTADO[e.value] for e in estados],
        "enlace": reverse("activos:lista"),
    }


def planes_pendientes():
    """Planes vencidos o próximos de equipos que aún no están en taller."""
    planes = PlanMantenimiento.objects.select_related("activo").exclude(
        activo__estado__in=[Activo.Estado.DADO_DE_BAJA, Activo.Estado.MANTENIMIENTO]
    )
    vencidos, proximos = [], []
    for plan in planes:
        if plan.vencido:
            vencidos.append(plan)
        elif plan.proxima:
            proximos.append(plan)
    return vencidos, proximos


def cobros_pendientes():
    qs = Cobro.objects.filter(estado=Cobro.Estado.PENDIENTE)
    return qs, qs.aggregate(t=Sum("total"))["t"] or 0


def resumen(usuario):
    rol = rol_de(usuario)
    hoy = timezone.localdate()
    datos = {"rol": rol, "hoy": hoy.isoformat(), "kpis": [], "tablas": [], "grafico": None}

    atrasados = Prestamo.objects.filter(estado=P.ATRASADO).select_related("contratista", "obra")
    bloqueados = Contratista.objects.filter(estado=Contratista.Estado.BLOQUEADO)
    lista_prestamos = reverse("prestamos:lista")

    if rol == ADMIN:
        vencidos, _ = planes_pendientes()
        _, total_pend = cobros_pendientes()
        solicitudes = Alerta.objects.filter(
            resuelta=False, tipo__in=[Alerta.Tipo.SOLICITUD_DESBLOQUEO, Alerta.Tipo.SOLICITUD_BAJA]
        )
        datos["kpis"] = [
            kpi("Préstamos atrasados", atrasados.count(), critico=True, enlace=f"{lista_prestamos}?estado=ATRASADO"),
            kpi("Contratistas bloqueados", bloqueados.count(), critico=True, enlace=reverse("contratistas:lista") + "?estado=BLOQUEADO"),
            kpi("Cobros pendientes", total_pend, "clp", enlace=reverse("prestamos:cobros")),
            kpi("Mantenciones vencidas", len(vencidos), critico=True, enlace=reverse("mantenimiento:lista")),
        ]
        datos["grafico"] = grafico_estados()
        datos["tablas"] = [
            tabla("Solicitudes por aprobar", [
                {"clave": "mensaje", "titulo": "Solicitud", "tipo": "enlace"},
                {"clave": "fecha", "titulo": "Fecha", "tipo": "fechahora"},
            ], [
                {"mensaje": {"texto": a.mensaje, "url": a.enlace}, "fecha": a.fecha.isoformat()} for a in solicitudes[:6]
            ], "No hay solicitudes de desbloqueo ni de baja.", reverse("alertas:lista")),
            tabla("Préstamos atrasados", COLS_PRESTAMO, [fila_prestamo(p) for p in atrasados[:6]],
                  "Ningún préstamo atrasado.", f"{lista_prestamos}?estado=ATRASADO"),
            tabla("Contratistas bloqueados", [
                {"clave": "nombre", "titulo": "Contratista", "tipo": "enlace"},
                {"clave": "motivo", "titulo": "Motivo"},
                {"clave": "fecha", "titulo": "Desde", "tipo": "fechahora"},
                {"clave": "accion", "titulo": "", "tipo": "accion"},
            ], [{
                "nombre": {"texto": c.razon_social, "url": c.get_absolute_url()},
                "motivo": c.motivo_bloqueo,
                "fecha": c.fecha_bloqueo.isoformat() if c.fecha_bloqueo else None,
                "accion": {"texto": "Revisar", "url": c.get_absolute_url()},
            } for c in bloqueados[:6]], "Ningún contratista bloqueado.", reverse("contratistas:lista") + "?estado=BLOQUEADO"),
        ]

    elif rol == BODEGUERO:
        vencidos, proximos = planes_pendientes()
        en_mant = Activo.objects.filter(estado=Activo.Estado.MANTENIMIENTO).select_related("categoria")
        datos["kpis"] = [
            kpi("Mantenciones vencidas", len(vencidos), critico=True, enlace=reverse("mantenimiento:lista")),
            kpi("Mantenciones próximas", len(proximos), enlace=reverse("mantenimiento:lista")),
            kpi("En mantenimiento", en_mant.count(), enlace=reverse("activos:lista") + "?estado=MANTENIMIENTO"),
            kpi("Disponibles en bodega", Activo.objects.filter(estado=Activo.Estado.DISPONIBLE, activo=True).count(),
                enlace=reverse("activos:lista") + "?estado=DISPONIBLE"),
        ]
        datos["grafico"] = grafico_estados()
        registrar = reverse("mantenimiento:registrar")
        datos["tablas"] = [
            tabla("Mantenciones por hacer", [
                {"clave": "codigo", "titulo": "Código", "tipo": "folio"},
                {"clave": "nombre", "titulo": "Activo"},
                {"clave": "criterio", "titulo": "Margen"},
                {"clave": "situacion", "titulo": "Situación", "tipo": "timbre"},
                {"clave": "accion", "titulo": "", "tipo": "accion"},
            ], [{
                "codigo": {"texto": p.activo.codigo, "url": p.activo.get_absolute_url()},
                "nombre": p.activo.nombre,
                "criterio": p.criterio,
                "situacion": {"estado": p.situacion, "texto": "Vencida" if p.vencido else "Próxima"},
                "accion": {"texto": "Registrar", "url": f"{registrar}?activo={p.activo.codigo}"},
            } for p in (vencidos + proximos)[:8]], "Todos los equipos tienen su mantención al día.", reverse("mantenimiento:lista")),
            tabla("En taller ahora", [
                {"clave": "codigo", "titulo": "Código", "tipo": "folio"},
                {"clave": "nombre", "titulo": "Activo"},
                {"clave": "motivo", "titulo": "Motivo"},
                {"clave": "accion", "titulo": "", "tipo": "accion"},
            ], [{
                "codigo": {"texto": a.codigo, "url": a.get_absolute_url()},
                "nombre": a.nombre,
                "motivo": (HistorialEstado.objects.filter(activo=a, estado_nuevo="MANTENIMIENTO").values_list("motivo", flat=True).first() or "—"),
                "accion": {"texto": "Finalizar", "url": f"{registrar}?activo={a.codigo}"},
            } for a in en_mant[:8]], "No hay equipos en taller.", reverse("activos:lista") + "?estado=MANTENIMIENTO"),
        ]

    elif rol == ENCARGADO:
        por_entregar = Prestamo.objects.filter(estado=P.BORRADOR).select_related("contratista", "obra").order_by("fecha_entrega")
        esperadas = Prestamo.objects.filter(
            estado__in=Prestamo.EN_TERRENO, fecha_devolucion_pactada__lte=hoy + timedelta(days=2)
        ).select_related("contratista", "obra").order_by("fecha_devolucion_pactada")
        danos_mes = DetallePrestamo.objects.filter(
            prestamo__fecha_devolucion_real__gte=hoy.replace(day=1),
            estado_llegada__in=[DetallePrestamo.EstadoFisico.DANADO, DetallePrestamo.EstadoFisico.FALTANTE],
        ).count()
        datos["kpis"] = [
            kpi("Entregas por hacer", por_entregar.count(), enlace=f"{lista_prestamos}?estado=BORRADOR"),
            kpi("Devoluciones hoy", esperadas.filter(fecha_devolucion_pactada=hoy).count(), enlace=f"{lista_prestamos}?estado=ENTREGADO"),
            kpi("Atrasados en terreno", atrasados.count(), critico=True, enlace=f"{lista_prestamos}?estado=ATRASADO"),
            kpi("Daños este mes", danos_mes),
        ]
        datos["tablas"] = [
            tabla("Entregas por hacer", COLS_PRESTAMO_ENTREGA, [
                {**fila_prestamo(p, {"texto": "Entregar", "url": reverse("prestamos:entregar", args=[p.codigo])}),
                 "fecha": p.fecha_entrega.isoformat()} for p in por_entregar[:8]
            ], "No hay entregas pendientes.", f"{lista_prestamos}?estado=BORRADOR"),
            tabla("Devoluciones esperadas", COLS_PRESTAMO + [{"clave": "accion", "titulo": "", "tipo": "accion"}], [
                fila_prestamo(p, {"texto": "Recibir", "url": reverse("prestamos:devolver", args=[p.codigo])})
                for p in esperadas[:8]
            ], "No se esperan devoluciones en los próximos 2 días.", f"{lista_prestamos}?estado=ENTREGADO"),
        ]

    elif rol == VENTAS:
        en_terreno = Prestamo.objects.filter(estado__in=Prestamo.EN_TERRENO)
        pendientes, total_pend = cobros_pendientes()
        vencen = en_terreno.filter(fecha_devolucion_pactada__lte=hoy + timedelta(days=7)).select_related(
            "contratista", "obra").order_by("fecha_devolucion_pactada")
        datos["kpis"] = [
            kpi("Préstamos atrasados", atrasados.count(), critico=True, enlace=f"{lista_prestamos}?estado=ATRASADO"),
            kpi("Préstamos en terreno", en_terreno.count(), enlace=f"{lista_prestamos}?estado=ENTREGADO"),
            kpi("Cobros pendientes", total_pend, "clp", enlace=reverse("prestamos:cobros")),
            kpi("Contratistas bloqueados", bloqueados.count(), critico=True, enlace=reverse("contratistas:lista") + "?estado=BLOQUEADO"),
        ]
        datos["grafico"] = grafico_facturacion(hoy)
        datos["tablas"] = [
            tabla("Préstamos que vencen esta semana", COLS_PRESTAMO, [fila_prestamo(p) for p in vencen[:8]],
                  "Ningún préstamo vence en los próximos 7 días.", lista_prestamos),
            tabla("Cobros por cobrar", [
                {"clave": "folio", "titulo": "Préstamo", "tipo": "folio"},
                {"clave": "contratista", "titulo": "Contratista"},
                {"clave": "total", "titulo": "Total", "tipo": "clp"},
            ], [{
                "folio": {"texto": c.prestamo.codigo, "url": reverse("prestamos:cobro", args=[c.pk])},
                "contratista": c.prestamo.contratista.razon_social,
                "total": c.total,
            } for c in pendientes.select_related("prestamo__contratista")[:6]], "No hay cobros pendientes.", reverse("prestamos:cobros")),
        ]

    datos["alertas"] = [
        {"id": a.id, "nivel": a.nivel, "tipo": a.get_tipo_display(), "mensaje": a.mensaje, "enlace": a.enlace,
         "fecha": a.fecha.isoformat()}
        for a in alertas_para(usuario).filter(resuelta=False).annotate(
            orden=Case(When(nivel=Alerta.Nivel.CRITICO, then=0), When(nivel=Alerta.Nivel.WARNING, then=1), default=2)
        ).order_by("orden", "-fecha")[:6]
    ]
    return datos


def grafico_facturacion(hoy):
    desde = (hoy.replace(day=1) - timedelta(days=150)).replace(day=1)
    meses = (
        Cobro.objects.filter(prestamo__fecha_devolucion_real__gte=desde)
        .annotate(mes=TruncMonth("prestamo__fecha_devolucion_real")).values("mes").annotate(total=Sum("total"))
    )
    por_mes = {m["mes"].strftime("%Y-%m"): m["total"] for m in meses if m["mes"]}
    etiquetas, valores, cursor = [], [], desde
    nombres = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    for _ in range(6):
        clave = cursor.strftime("%Y-%m")
        etiquetas.append(f"{nombres[cursor.month - 1]} {cursor.year % 100:02d}")
        valores.append(por_mes.get(clave, 0))
        cursor = (cursor + timedelta(days=32)).replace(day=1)
    return {"titulo": "Facturación por mes (CLP con IVA)", "tipo": "bar", "formato": "clp",
            "etiquetas": etiquetas, "valores": valores, "colores": ["#2E2A6E"] * 5 + ["#C8102E"],
            "enlace": reverse("prestamos:cobros")}


COLS_PRESTAMO = [
    {"clave": "folio", "titulo": "Folio", "tipo": "folio"},
    {"clave": "contratista", "titulo": "Contratista"},
    {"clave": "obra", "titulo": "Obra"},
    {"clave": "fecha", "titulo": "Devolución", "tipo": "fecha"},
    {"clave": "estado", "titulo": "Estado", "tipo": "timbre"},
]

COLS_PRESTAMO_ENTREGA = [
    {"clave": "folio", "titulo": "Folio", "tipo": "folio"},
    {"clave": "contratista", "titulo": "Contratista"},
    {"clave": "obra", "titulo": "Obra"},
    {"clave": "fecha", "titulo": "Entrega", "tipo": "fecha"},
    {"clave": "accion", "titulo": "", "tipo": "accion"},
]
