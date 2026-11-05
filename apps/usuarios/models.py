from django.contrib.auth.models import AbstractUser
from django.db import models

from . import roles


class Usuario(AbstractUser):
    rut = models.CharField("RUT", max_length=12, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    cargo = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def rol(self):
        """Rol principal del usuario (el superusuario cuenta como Administrador)."""
        return roles.rol_de(self)

    def __str__(self):
        return self.get_full_name() or self.username
