from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from apps.alertas.models import Alerta
from apps.alertas.services import crear_alerta
from apps.usuarios.permissions import RolRequeridoMixin
from apps.usuarios.roles import ADMIN, BODEGUERO, VENTAS

from . import services
from .forms import ActivoForm, ItemFormSet, PaqueteForm
from .models import Activo, Bodega, CategoriaActivo, PaqueteMaquinaria

VENTANA_DIAS = 180


def linea_de_estados(activo, dias=VENTANA_DIAS):
    """Tramos de estado de los últimos `dias`, todos en la misma escala, para la hoja de vida."""
    ahora = timezone.now()
    inicio = ahora - timedelta(days=dias)
    eventos = list(activo.historial.order_by("fecha", "id").values_list("fecha", "estado_nuevo"))
    if not eventos:
        return []
    tramos = []
    if eventos[0][0] > inicio:
        tramos.append({"estado": None, "desde": inicio, "hasta": eventos[0][0]})
    for i, (fecha, estado) in enumerate(eventos):
        hasta = eventos[i + 1][0] if i + 1 < len(eventos) else ahora
        if hasta > inicio:
            tramos.append({"estado": estado, "desde": max(fecha, inicio), "hasta": hasta})
    total = (ahora - inicio).total_seconds()
    etiquetas = dict(Activo.Estado.choices)
    salida = []
    for t in tramos:
        ancho = (t["hasta"] - t["desde"]).total_seconds() / total * 100
        if ancho <= 0:
            continue
        salida.append({
            "estado": t["estado"] or "SIN_REGISTRO",
            "etiqueta": etiquetas.get(t["estado"], "Antes del alta"),
            "desde": t["desde"], "hasta": t["hasta"], "ancho": round(ancho, 3),
            "dias": max(1, round((t["hasta"] - t["desde"]).total_seconds() / 86400)),
        })
    return salida


class ListaView(RolRequeridoMixin, TemplateView):
    template_name = "activos/lista.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            categorias=CategoriaActivo.objects.all(), bodegas=Bodega.objects.all(), estados=Activo.Estado.choices, **kwargs
        )


class FichaView(RolRequeridoMixin, DetailView):
    template_name = "activos/ficha.html"
    slug_field = slug_url_kwarg = "codigo"
    queryset = Activo.objects.select_related("categoria", "bodega_actual", "plan")

    def get_context_data(self, **kwargs):
        a = self.object
        prestamos = a.detalles_prestamo.select_related("prestamo__contratista", "prestamo__obra").order_by("-prestamo__creado")
        return super().get_context_data(
            plan=getattr(a, "plan", None),
            linea=linea_de_estados(a),
            ventana=VENTANA_DIAS,
            historial=a.historial.select_related("usuario")[:30],
            prestamos=prestamos[:15],
            mantenimientos=a.mantenimientos.all()[:15],
            traslados=a.traslados.select_related("bodega_origen", "bodega_destino", "usuario")[:15],
            bodegas=Bodega.objects.exclude(pk=a.bodega_actual_id),
            **kwargs,
        )


class CrearView(RolRequeridoMixin, CreateView):
    roles = (BODEGUERO,)
    form_class = ActivoForm
    template_name = "activos/form.html"

    def form_valid(self, form):
        datos = {k: v for k, v in form.cleaned_data.items()}
        self.object = services.crear_activo(self.request.user, **datos)
        messages.success(self.request, f"Activo {self.object.codigo} creado. Imprime su etiqueta QR.")
        return redirect(self.object)


class EditarView(RolRequeridoMixin, UpdateView):
    roles = (BODEGUERO,)
    form_class = ActivoForm
    template_name = "activos/form.html"
    slug_field = slug_url_kwarg = "codigo"
    model = Activo

    def form_valid(self, form):
        messages.success(self.request, "Cambios guardados.")
        return super().form_valid(form)


class SolicitarBajaView(RolRequeridoMixin, View):
    roles = (BODEGUERO,)

    def post(self, request, codigo):
        activo = get_object_or_404(Activo, codigo=codigo)
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Escribe el motivo de la baja.")
        else:
            crear_alerta(Alerta.Tipo.SOLICITUD_BAJA, f"{request.user} solicita dar de baja {activo.codigo}: {motivo}",
                         objeto=activo, nivel=Alerta.Nivel.WARNING, rol_destino=ADMIN)
            messages.success(request, "Solicitud de baja enviada al Administrador.")
        return redirect(activo)


class QRView(RolRequeridoMixin, View):
    def get(self, request, codigo):
        activo = get_object_or_404(Activo, codigo=codigo)
        return HttpResponse(services.qr_png(activo, request), content_type="image/png")


class EtiquetasView(RolRequeridoMixin, TemplateView):
    roles = (BODEGUERO,)
    template_name = "activos/etiquetas.html"

    def get_context_data(self, **kwargs):
        ids = [i for i in self.request.GET.getlist("ids") if i.isdigit()]
        seleccion = Activo.objects.filter(pk__in=ids).select_related("categoria") if ids else None
        return super().get_context_data(
            seleccion=seleccion,
            activos=Activo.objects.filter(activo=True).select_related("categoria", "bodega_actual"),
            **kwargs,
        )


class EscanearView(RolRequeridoMixin, TemplateView):
    template_name = "activos/escanear.html"


class BodegasView(RolRequeridoMixin, ListView):
    roles = (BODEGUERO,)
    template_name = "activos/bodegas.html"
    context_object_name = "bodegas"

    def get_queryset(self):
        return Bodega.objects.select_related("obra", "encargado")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for b in ctx["bodegas"]:
            b.inventario = b.activos.filter(activo=True).select_related("categoria", "plan")
            b.conteo = {e: 0 for e, _ in Activo.Estado.choices}
            for a in b.inventario:
                b.conteo[a.estado] += 1
        return ctx


class PaquetesView(RolRequeridoMixin, ListView):
    template_name = "activos/paquetes.html"
    context_object_name = "paquetes"

    def get_queryset(self):
        return PaqueteMaquinaria.objects.prefetch_related("items__categoria")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        conteo = services.disponibles_por_categoria()
        for p in ctx["paquetes"]:
            p.disp = services.disponibilidad_paquete(p, conteo)
        return ctx


class PaqueteFormMixin(RolRequeridoMixin):
    roles = (VENTAS,)
    model = PaqueteMaquinaria
    form_class = PaqueteForm
    template_name = "activos/paquete_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = kwargs.get("items") or ItemFormSet(instance=getattr(self, "object", None))
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if kwargs.get("pk") else None
        form = self.get_form()
        items = ItemFormSet(request.POST, instance=self.object or PaqueteMaquinaria())
        if form.is_valid() and items.is_valid():
            paquete = form.save(commit=False)
            if not paquete.pk:
                paquete.creado_por = request.user
            paquete.save()
            items.instance = paquete
            items.save()
            messages.success(request, f"Paquete «{paquete.nombre}» guardado.")
            return redirect("activos:paquetes")
        return self.render_to_response(self.get_context_data(form=form, items=items))


class PaqueteCrearView(PaqueteFormMixin, CreateView):
    pass


class PaqueteEditarView(PaqueteFormMixin, UpdateView):
    pass
