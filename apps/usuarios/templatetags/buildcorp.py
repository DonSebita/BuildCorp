from django import template
from django.utils.html import format_html

from apps.usuarios.roles import tiene_rol

register = template.Library()

ESTADOS = {
    # estado: (clase css, etiqueta)
    "DISPONIBLE": ("ok", "Disponible"),
    "EN_USO": ("uso", "En uso"),
    "MANTENIMIENTO": ("warn", "Mantenimiento"),
    "DADO_DE_BAJA": ("baja", "Dado de baja"),
    "BORRADOR": ("info", "Por entregar"),
    "ENTREGADO": ("uso", "Entregado"),
    "ATRASADO": ("crit", "Atrasado"),
    "DEVUELTO": ("ok", "Devuelto"),
    "CERRADO": ("cerrado", "Cerrado"),
    "ACTIVO": ("ok", "Activo"),
    "BLOQUEADO": ("crit", "Bloqueado"),
    "PENDIENTE": ("warn", "Pendiente"),
    "PAGADO": ("ok", "Pagado"),
    "EN_CURSO": ("warn", "En curso"),
    "FINALIZADA": ("ok", "Finalizada"),
    "CRITICO": ("crit", "Crítico"),
    "WARNING": ("warn", "Atención"),
    "INFO": ("info", "Aviso"),
    "VENCIDO": ("crit", "Vencido"),
    "PROXIMO": ("warn", "Próximo"),
    "AL_DIA": ("ok", "Al día"),
}


@register.filter
def clp(valor):
    """Formatea un entero como pesos chilenos: 1250000 -> $1.250.000."""
    if valor in (None, ""):
        return "—"
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return valor
    signo = "-" if n < 0 else ""
    return f"{signo}${abs(n):,}".replace(",", ".")


@register.filter
def miles(valor):
    if valor in (None, ""):
        return "—"
    return f"{int(valor):,}".replace(",", ".")


@register.simple_tag
def timbre(estado, texto=None):
    """Badge de estado con forma de timbre. Siempre lleva texto, no solo color."""
    clase, etiqueta = ESTADOS.get(estado, ("info", estado))
    return format_html('<span class="timbre timbre-{}">{}</span>', clase, texto or etiqueta)


@register.filter
def puede(usuario, roles_csv):
    """{% if user|puede:"Bodeguero,Ventas" %} — el Admin siempre puede."""
    return tiene_rol(usuario, *[r.strip() for r in roles_csv.split(",") if r.strip()])
