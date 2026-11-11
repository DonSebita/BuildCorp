from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View

from apps.activos.models import Activo, PaqueteMaquinaria
from apps.activos.services import disponibilidad_paquete, disponibles_por_categoria, qr_png
from apps.contratistas.models import Contratista
from apps.usuarios.forms import EstiloMixin
from apps.usuarios.permissions import RolRequeridoMixin
from apps.usuarios.roles import BODEGUERO, ENCARGADO, VENTAS

from . import services
from .models import Cobro, DetallePrestamo, ParametroSistema, Prestamo

TODOS_LEEN = (VENTAS, BODEGUERO, ENCARGADO)


class PrestamoMixin:
    def get_object(self, queryset=None):
        return get_object_or_404(
            Prestamo.objects.select_related("contratista", "obra", "creado_por", "entregado_por", "recibido_por"),
            codigo=self.kwargs["codigo"],
        )


class ListaView(RolRequeridoMixin, TemplateView):
    roles = TODOS_LEEN
    template_name = "prestamos/lista.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(estados=Prestamo.Estado.choices, **kwargs)


class NuevoView(RolRequeridoMixin, TemplateView):
    roles = (VENTAS,)
    template_name = "prestamos/nuevo.html"

    def get_context_data(self, **kwargs):
        conteo = disponibles_por_categoria()
        activos = Activo.objects.filter(estado=Activo.Estado.DISPONIBLE, activo=True).select_related("categoria", "plan")
        paquetes = list(PaqueteMaquinaria.objects.filter(activo=True).prefetch_related("items__categoria"))
        for p in paquetes:
            p.disp = disponibilidad_paquete(p, conteo)
            p.faltan = ", ".join(i["categoria"].lower() for i in p.disp["items"] if not i["alcanza"])
        return super().get_context_data(
            contratistas=Contratista.objects.prefetch_related("obras"),
            paquetes=paquetes,
            activos=[a for a in activos if not (getattr(a, "plan", None) and a.plan.vencido)],
            conteo=conteo,
            **kwargs,
        )


class DetalleView(RolRequeridoMixin, PrestamoMixin, DetailView):
    roles = TODOS_LEEN
    template_name = "prestamos/detalle.html"
    context_object_name = "prestamo"

    def get_context_data(self, **kwargs):
        p = self.object
        ctx = super().get_context_data(**kwargs)
        ctx["paquetes"] = p.paquetes.select_related("paquete").prefetch_related("detalles__activo", "paquete__items__categoria")
        ctx["sueltos"] = p.detalles.filter(prestamo_paquete__isnull=True).select_related("activo__categoria")
        ctx["firmas"] = {f.tipo: f for f in p.firmas.all()}
        ctx["cobro"] = getattr(p, "cobro", None)
        if p.en_terreno:
            ctx["estimado"] = services.desglose(p)
        return ctx


class EntregarView(RolRequeridoMixin, PrestamoMixin, DetailView):
    roles = (ENCARGADO,)
    template_name = "prestamos/entregar.html"
    context_object_name = "prestamo"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.estado != Prestamo.Estado.BORRADOR:
            messages.info(request, f"{self.object.codigo} ya fue entregado.")
            return redirect(self.object)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        return super().get_context_data(estados_fisicos=DetallePrestamo.EstadoFisico.choices[:2], **kwargs)


class DevolverView(RolRequeridoMixin, PrestamoMixin, DetailView):
    roles = (ENCARGADO,)
    template_name = "prestamos/devolver.html"
    context_object_name = "prestamo"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.en_terreno:
            messages.info(request, f"{self.object.codigo} no está en terreno.")
            return redirect(self.object)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        p = self.object
        return super().get_context_data(
            detalles=p.detalles.select_related("activo__categoria", "prestamo_paquete__paquete"),
            estados_fisicos=DetallePrestamo.EstadoFisico.choices,
            estimado=services.desglose(p),
            **kwargs,
        )


class ComprobanteView(RolRequeridoMixin, PrestamoMixin, DetailView):
    roles = TODOS_LEEN
    template_name = "prestamos/comprobante.html"
    context_object_name = "prestamo"

    def get_context_data(self, **kwargs):
        p = self.object
        return super().get_context_data(
            detalles=p.detalles.select_related("activo__categoria", "prestamo_paquete__paquete"),
            firmas={f.tipo: f for f in p.firmas.all()},
            cobro=getattr(p, "cobro", None),
            **kwargs,
        )


class QRView(RolRequeridoMixin, View):
    """QR del pack arrendado: abre el detalle del préstamo con todas sus máquinas."""
    roles = TODOS_LEEN

    def get(self, request, codigo):
        prestamo = get_object_or_404(Prestamo, codigo=codigo)
        return HttpResponse(qr_png(prestamo, request), content_type="image/png")


class EtiquetaView(RolRequeridoMixin, PrestamoMixin, DetailView):
    """Etiqueta imprimible del pack: un QR y la lista de códigos que lo forman."""
    roles = TODOS_LEEN
    template_name = "prestamos/etiqueta.html"
    context_object_name = "prestamo"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            detalles=self.object.detalles.select_related("activo__categoria", "prestamo_paquete__paquete").order_by("activo__codigo"),
            **kwargs,
        )


class CobrosView(RolRequeridoMixin, ListView):
    roles = (VENTAS,)
    template_name = "prestamos/cobros.html"
    context_object_name = "cobros"

    def get_queryset(self):
        qs = Cobro.objects.select_related("prestamo__contratista")
        if estado := self.request.GET.get("estado"):
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        totales = Cobro.objects.values("estado").annotate(t=Sum("total"))
        return super().get_context_data(totales={t["estado"]: t["t"] for t in totales}, **kwargs)


class CobroView(RolRequeridoMixin, DetailView):
    roles = (VENTAS,)
    model = Cobro
    template_name = "prestamos/cobro.html"

    def get_context_data(self, **kwargs):
        p = self.object.prestamo
        return super().get_context_data(
            prestamo=p,
            paquetes=p.paquetes.select_related("paquete"),
            sueltos=p.detalles.filter(prestamo_paquete__isnull=True).select_related("activo"),
            danos=p.detalles.filter(cargo_dano__gt=0).select_related("activo"),
            params=ParametroSistema.actual(),
            **kwargs,
        )


class PagarView(RolRequeridoMixin, View):
    roles = (VENTAS,)

    def post(self, request, pk):
        cobro = get_object_or_404(Cobro, pk=pk)
        try:
            services.registrar_pago(cobro, request.user)
            messages.success(request, f"Pago de {cobro.prestamo.codigo} registrado. El préstamo quedó cerrado.")
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        return redirect("prestamos:cobro", pk=pk)


class ParametrosForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = ParametroSistema
        fields = ["dias_gracia", "recargo_atraso", "tasa_iva"]


class ParametrosView(RolRequeridoMixin, UpdateView):
    roles = ()
    form_class = ParametrosForm
    template_name = "form.html"
    extra_context = {"titulo": "Parámetros del sistema",
                     "ayuda": "Afectan a los cobros que se calculen desde ahora; los préstamos ya creados mantienen sus tarifas."}

    def get_object(self, queryset=None):
        return ParametroSistema.actual()

    def form_valid(self, form):
        messages.success(self.request, "Parámetros actualizados.")
        form.save()
        return redirect("prestamos:parametros")
