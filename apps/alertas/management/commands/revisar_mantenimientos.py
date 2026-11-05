from django.core.management.base import BaseCommand

from apps.mantenimiento.services import revisar_mantenimientos


class Command(BaseCommand):
    help = "Revisa los planes de mantención por usos, horas y días, y crea alertas."

    def handle(self, *args, **opts):
        r = revisar_mantenimientos()
        self.stdout.write(self.style.SUCCESS(
            f"Vencidas: {r['VENCIDO']} · Próximas: {r['PROXIMO']} · Al día: {r['AL_DIA']}"
        ))
