"""Modelos para ofertas laborales y oportunidades de emprendimiento."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Oportunidad(models.Model):
    """Oferta pública con fuente, vigencia y responsable."""

    class Tipo(models.TextChoices):
        """Tipos de oportunidad publicados por el centro."""

        LABORAL = 'LABORAL', 'Oferta laboral'
        EMPRENDIMIENTO = 'EMPRENDIMIENTO', 'Emprendimiento'
        FORMACION = 'FORMACION', 'Convocatoria formativa'

    titulo = models.CharField(max_length=180)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descripcion = models.TextField()
    fuente = models.CharField(max_length=180)
    enlace = models.URLField(blank=True)
    vigente_hasta = models.DateField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='oportunidades_responsable',
    )
    publicada = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Muestra primero las publicaciones vigentes más recientes."""

        ordering = ['-creada_en']
        indexes = [models.Index(fields=['publicada', 'vigente_hasta'])]
        verbose_name = 'oportunidad'
        verbose_name_plural = 'oportunidades'

    def __str__(self):
        """Devuelve el título de la oportunidad."""

        return self.titulo

    @property
    def esta_vigente(self):
        """Indica si la oportunidad está publicada y no ha vencido."""

        return self.publicada and self.vigente_hasta >= timezone.localdate()
