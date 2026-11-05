from django.views.generic import TemplateView

from apps.usuarios.permissions import RolRequeridoMixin


class BandejaView(RolRequeridoMixin, TemplateView):
    """La bandeja se llena con fetch desde /api/v1/alertas/."""

    template_name = "alertas/bandeja.html"
