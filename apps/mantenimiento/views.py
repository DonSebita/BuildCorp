from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.activos.models import Activo
from apps.usuarios.forms import EstiloMixin
from apps.usuarios.permissions import RolRequeridoMixin
from apps.usuarios.roles import BODEGUERO

from . import services
from .models import Mantenimiento, PlanMantenimiento


class MantenimientoForm(EstiloMixin, forms.ModelForm):
    codigo = forms.CharField(label="Código del activo", max_length=12,
                             widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "RTM-0004"}))

    class Meta:
        model = Mantenimiento
        fields = ["tipo", "estado", "fecha", "tecnico", "costo", "descripcion"]
        widgets = {"fecha": forms.DateInput()}
        labels = {"estado": "¿Terminó la mantención?"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = [
            (Mantenimiento.Estado.FINALIZADA, "Sí, el equipo queda disponible"),
            (Mantenimiento.Estado.EN_CURSO, "No, sigue en taller"),
        ]
        self.order_fields(["codigo"])

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        try:
            self.activo = Activo.objects.select_related("plan").get(codigo=codigo)
        except Activo.DoesNotExist:
            raise forms.ValidationError(f"No existe el activo {codigo}.")
        if self.activo.estado == Activo.Estado.DADO_DE_BAJA:
            raise forms.ValidationError(f"{codigo} está dado de baja.")
        if self.activo.estado == Activo.Estado.EN_USO:
            raise forms.ValidationError(f"{codigo} está en terreno. Regístrala cuando vuelva.")
        return codigo


class ListaView(RolRequeridoMixin, TemplateView):
    roles = (BODEGUERO,)
    template_name = "mantenimiento/lista.html"

    def get_context_data(self, **kwargs):
        planes = PlanMantenimiento.objects.select_related("activo__categoria").exclude(
            activo__estado__in=["DADO_DE_BAJA", "MANTENIMIENTO"]
        )
        vencidos, proximos = [], []
        for p in planes:
            (vencidos if p.vencido else proximos if p.proxima else []).append(p)
        return super().get_context_data(
            vencidos=vencidos,
            proximos=proximos,
            en_taller=Activo.objects.filter(estado=Activo.Estado.MANTENIMIENTO).select_related("categoria"),
            historial=Mantenimiento.objects.select_related("activo", "registrado_por")[:30],
            **kwargs,
        )


class RegistrarView(RolRequeridoMixin, FormView):
    roles = (BODEGUERO,)
    form_class = MantenimientoForm
    template_name = "mantenimiento/registrar.html"

    def get_initial(self):
        return {"codigo": self.request.GET.get("activo", "")}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        codigo = self.request.GET.get("activo") or self.request.POST.get("codigo")
        if codigo:
            ctx["activo"] = Activo.objects.select_related("plan", "categoria").filter(codigo=codigo.strip().upper()).first()
        return ctx

    def form_valid(self, form):
        datos = {k: v for k, v in form.cleaned_data.items() if k != "codigo"}
        mant = services.registrar_mantenimiento(form.activo, self.request.user, **datos)
        if mant.estado == Mantenimiento.Estado.FINALIZADA:
            messages.success(self.request, f"Mantención {mant.folio} registrada. {form.activo.codigo} quedó disponible.")
        else:
            messages.success(self.request, f"Mantención {mant.folio} abierta. {form.activo.codigo} sigue en taller.")
        return redirect(form.activo)
