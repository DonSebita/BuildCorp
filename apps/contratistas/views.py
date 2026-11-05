from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from apps.usuarios.forms import EstiloMixin
from apps.usuarios.permissions import RolRequeridoMixin
from apps.usuarios.roles import ADMIN, BODEGUERO, ENCARGADO, VENTAS, rol_de

from . import services
from .models import Contratista, Obra

LECTURA = (VENTAS, BODEGUERO, ENCARGADO)


class ContratistaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Contratista
        fields = ["rut", "razon_social", "contacto", "email", "telefono"]


class ObraForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Obra
        fields = ["nombre", "direccion", "responsable_nombre", "responsable_rut", "fecha_inicio", "fecha_fin", "activa"]
        widgets = {"fecha_inicio": forms.DateInput(), "fecha_fin": forms.DateInput()}


class ListaView(RolRequeridoMixin, ListView):
    roles = LECTURA
    template_name = "contratistas/lista.html"
    context_object_name = "contratistas"

    def get_queryset(self):
        qs = Contratista.objects.annotate(
            n_obras=Count("obras", filter=Q(obras__activa=True), distinct=True),
            en_terreno=Count("prestamos", filter=Q(prestamos__estado__in=["ENTREGADO", "ATRASADO"]), distinct=True),
            atrasados=Count("prestamos", filter=Q(prestamos__estado="ATRASADO"), distinct=True),
        )
        if estado := self.request.GET.get("estado"):
            qs = qs.filter(estado=estado)
        if q := self.request.GET.get("q", "").strip():
            qs = qs.filter(Q(razon_social__icontains=q) | Q(rut__icontains=q) | Q(contacto__icontains=q))
        return qs


class DetalleView(RolRequeridoMixin, DetailView):
    roles = LECTURA
    model = Contratista
    template_name = "contratistas/detalle.html"

    def get_context_data(self, **kwargs):
        c = self.object
        return super().get_context_data(
            obras=c.obras.all(),
            prestamos=c.prestamos.select_related("obra")[:20],
            **kwargs,
        )


class CrearView(RolRequeridoMixin, CreateView):
    roles = (VENTAS,)
    model = Contratista
    form_class = ContratistaForm
    template_name = "form.html"
    extra_context = {"titulo": "Nuevo contratista", "volver": "contratistas:lista"}


class EditarView(RolRequeridoMixin, UpdateView):
    roles = (VENTAS,)
    model = Contratista
    form_class = ContratistaForm
    template_name = "form.html"
    extra_context = {"titulo": "Editar contratista", "volver": "contratistas:lista"}


class ObraCrearView(RolRequeridoMixin, CreateView):
    roles = (VENTAS,)
    model = Obra
    form_class = ObraForm
    template_name = "form.html"

    def dispatch(self, request, *args, **kwargs):
        self.contratista = get_object_or_404(Contratista, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(titulo=f"Nueva obra de {self.contratista}", **kwargs)

    def form_valid(self, form):
        form.instance.contratista = self.contratista
        messages.success(self.request, "Obra registrada.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.contratista.get_absolute_url()


class ObraEditarView(RolRequeridoMixin, UpdateView):
    roles = (VENTAS,)
    model = Obra
    form_class = ObraForm
    template_name = "form.html"
    extra_context = {"titulo": "Editar obra"}

    def get_success_url(self):
        return self.object.contratista.get_absolute_url()


class BloqueoView(RolRequeridoMixin, View):
    """Admin: desbloquea. Ventas: solicita el desbloqueo."""

    roles = (VENTAS,)

    def post(self, request, pk):
        c = get_object_or_404(Contratista, pk=pk)
        motivo = request.POST.get("motivo", "")
        try:
            if rol_de(request.user) == ADMIN:
                services.desbloquear(c, request.user, motivo)
                messages.success(request, f"{c} desbloqueado. El motivo quedó registrado.")
            else:
                services.solicitar_desbloqueo(c, request.user, motivo)
                messages.success(request, "Solicitud enviada al Administrador.")
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        return redirect(reverse("contratistas:detalle", args=[c.pk]))
