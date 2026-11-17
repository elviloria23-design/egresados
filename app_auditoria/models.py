"""Modelos para trazabilidad de operaciones críticas."""

from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    """Almacena quién realizó una operación y su contexto."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_auditoria',
    )
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=100)
    entidad_id = models.CharField(max_length=64, blank=True)
    valores = models.JSONField(default=dict, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena la bitácora de lo más reciente a lo más antiguo."""

        ordering = ['-creado_en']
        verbose_name = 'registro de auditoría'
        verbose_name_plural = 'registros de auditoría'

    def __str__(self):
        """Devuelve una descripción legible del evento."""

        return f'{self.accion} · {self.entidad} #{self.entidad_id}'
