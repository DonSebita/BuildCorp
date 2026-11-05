from django.core.management.base import BaseCommand

from apps.prestamos.services import revisar_morosidad


class Command(BaseCommand):
    help = "Marca préstamos atrasados, crea alertas y bloquea contratistas que superan los días de gracia."

    def handle(self, *args, **opts):
        r = revisar_morosidad()
        self.stdout.write(self.style.SUCCESS(f"Atrasados: {r['atrasados']} · Bloqueados hoy: {r['bloqueados']}"))
