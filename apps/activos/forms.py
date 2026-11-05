from django import forms
from django.forms import inlineformset_factory

from apps.usuarios.forms import EstiloMixin

from .models import Activo, Bodega, ItemPaquete, PaqueteMaquinaria


class ActivoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Activo
        fields = ["categoria", "nombre", "marca", "modelo", "numero_serie", "fecha_adquisicion", "valor_compra",
                  "bodega_actual", "foto"]
        widgets = {"fecha_adquisicion": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # La categoría define el código, y la bodega cambia solo con un traslado.
            del self.fields["categoria"]
            del self.fields["bodega_actual"]


class TrasladoForm(EstiloMixin, forms.Form):
    bodega_destino = forms.ModelChoiceField(Bodega.objects.all(), label="Bodega de destino")
    observacion = forms.CharField(label="Observación", required=False)


class PaqueteForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = PaqueteMaquinaria
        fields = ["codigo", "nombre", "descripcion", "tarifa_diaria", "tarifa_mensual", "activo"]


class ItemForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = ItemPaquete
        fields = ["categoria", "cantidad"]


ItemFormSet = inlineformset_factory(
    PaqueteMaquinaria, ItemPaquete, form=ItemForm, extra=2, can_delete=True, min_num=1, validate_min=True
)
