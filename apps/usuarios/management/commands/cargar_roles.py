from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.usuarios.roles import TODOS


class Command(BaseCommand):
    help = "Crea los grupos de rol de BuildCorp (idempotente)."

    def handle(self, *args, **opts):
        for nombre in TODOS:
            _, creado = Group.objects.get_or_create(name=nombre)
            self.stdout.write(f"{'Creado' if creado else 'Ya existe'}: {nombre}")
