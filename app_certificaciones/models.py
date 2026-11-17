"""Modelos para certificaciones verificables de egresados."""

import uuid

from django.conf import settings
from django.db import models

from app_egresados.models import Egresado


class Certificacion(models.Model):
    """Certificación institucional con número y código de verificación únicos."""

    class Estado(models.TextChoices):
        """Estados disponibles para un documento institucional."""

        VIGENTE = 'VIGENTE', 'Vigente'
        ANULADA = 'ANULADA', 'Anulada'

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='certificaciones',
    )
    numero = models.CharField(max_length=32, unique=True)
    codigo_verificacion = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    tipo = models.CharField(max_length=120)
    motivo = models.CharField(max_length=300)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.VIGENTE,
    )
    emitida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='certificaciones_emitidas',
    )
    emitida_en = models.DateTimeField(auto_now_add=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificaciones_anuladas',
    )
    anulacion_motivo = models.TextField(blank=True)
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Ordena las certificaciones desde la más reciente."""

        ordering = ['-emitida_en']
        permissions = [
            (
                'emitir_certificaciones',
                'Puede emitir certificaciones a egresados',
            ),
            (
                'anular_certificaciones',
                'Puede anular certificaciones emitidas',
            ),
        ]
        verbose_name = 'certificación'
        verbose_name_plural = 'certificaciones'

    def __str__(self):
        """Devuelve el número y tipo de certificado."""

        return f'{self.numero} · {self.tipo}'
