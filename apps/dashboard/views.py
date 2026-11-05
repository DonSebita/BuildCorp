import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.views.generic import TemplateView, View

from apps.activos.models import Activo
from apps.prestamos.models import Cobro, Prestamo
from apps.usuarios.permissions import RolRequeridoMixin
from apps.usuarios.roles import BODEGUERO, VENTAS, tiene_rol


class InicioView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/inicio.html"


EXPORTABLES = {
    "activos": (
        lambda: Activo.objects.select_related("categoria", "bodega_actual"),
        ["Código", "Nombre", "Categoría", "Estado", "Bodega", "Usos", "Horas"],
        lambda a: [a.codigo, a.nombre, a.categoria.nombre, a.get_estado_display(),
                   a.bodega_actual or "", a.usos_totales, a.horas_uso_totales],
    ),
    "prestamos": (
        lambda: Prestamo.objects.select_related("contratista", "obra"),
        ["Folio", "Contratista", "Obra", "Entrega", "Devolución pactada", "Devolución real", "Estado"],
        lambda p: [p.codigo, p.contratista, p.obra, p.fecha_entrega, p.fecha_devolucion_pactada,
                   p.fecha_devolucion_real or "", p.get_estado_display()],
    ),
    "cobros": (
        lambda: Cobro.objects.select_related("prestamo__contratista"),
        ["Préstamo", "Contratista", "Días", "Atraso", "Arriendo", "Recargo", "Daños", "Neto", "IVA", "Total", "Estado"],
        lambda c: [c.prestamo.codigo, c.prestamo.contratista, c.dias_cobrados, c.dias_atraso, c.monto_arriendo,
                   c.monto_atraso, c.monto_danos, c.neto, c.iva, c.total, c.get_estado_display()],
    ),
}


ROLES_EXPORTAR = {"activos": (VENTAS, BODEGUERO), "prestamos": (VENTAS,), "cobros": (VENTAS,)}


class ExportarCSVView(RolRequeridoMixin, View):
    roles = (VENTAS, BODEGUERO)

    def get(self, request, recurso):
        if recurso not in EXPORTABLES:
            raise Http404
        if not tiene_rol(request.user, *ROLES_EXPORTAR[recurso]):
            raise PermissionDenied
        consulta, cabecera, fila = EXPORTABLES[recurso]
        respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = f'attachment; filename="buildcorp-{recurso}.csv"'
        respuesta.write("﻿")  # BOM para que Excel abra bien los acentos
        writer = csv.writer(respuesta, delimiter=";")
        writer.writerow(cabecera)
        for obj in consulta():
            writer.writerow(fila(obj))
        return respuesta
