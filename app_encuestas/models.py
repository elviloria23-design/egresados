"""Modelos para definir encuestas y conservar sus respuestas."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from app_egresados.models import Egresado, ProgramaFormacion


class Encuesta(models.Model):
    """Encuesta de seguimiento publicada por un usuario autorizado."""

    titulo = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='encuestas_creadas',
    )
    programas = models.ManyToManyField(
        ProgramaFormacion,
        blank=True,
        related_name='encuestas',
    )
    publicada = models.BooleanField(default=False)
    inicia_en = models.DateField(default=timezone.localdate)
    finaliza_en = models.DateField()
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las encuestas por fecha de creación."""

        ordering = ['-creada_en']
        verbose_name = 'encuesta'
        verbose_name_plural = 'encuestas'

    def __str__(self):
        """Devuelve el título de la encuesta."""

        return self.titulo

    @property
    def esta_vigente(self):
        """Indica si la encuesta está publicada y dentro de su vigencia."""

        hoy = timezone.localdate()
        return self.publicada and self.inicia_en <= hoy <= self.finaliza_en


class Pregunta(models.Model):
    """Pregunta ordenada con validación y opciones tipadas."""

    class Tipo(models.TextChoices):
        """Tipos de respuesta admitidos."""

        TEXTO = 'TEXTO', 'Texto'
        OPCION = 'OPCION', 'Opción única'
        MULTIPLE = 'MULTIPLE', 'Selección múltiple'
        SI_NO = 'SI_NO', 'Sí o no'
        NUMERO = 'NUMERO', 'Número'

    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.CASCADE,
        related_name='preguntas',
    )
    texto = models.CharField(max_length=300)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    opciones = models.JSONField(default=list, blank=True)
    obligatoria = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=1)

    class Meta:
        """Ordena preguntas y evita repetir posición en una encuesta."""

        ordering = ['orden', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['encuesta', 'orden'],
                name='unique_survey_question_order',
            ),
        ]
        verbose_name = 'pregunta'
        verbose_name_plural = 'preguntas'

    def __str__(self):
        """Devuelve el texto de la pregunta."""

        return self.texto


class RespuestaEncuesta(models.Model):
    """Respuesta única de un egresado a una encuesta."""

    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.PROTECT,
        related_name='respuestas',
    )
    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='respuestas_encuesta',
    )
    respondida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Impide que un egresado responda varias veces la misma encuesta."""

        ordering = ['-respondida_en']
        constraints = [
            models.UniqueConstraint(
                fields=['encuesta', 'egresado'],
                name='unique_response_per_alumni_survey',
            ),
        ]
        verbose_name = 'respuesta de encuesta'
        verbose_name_plural = 'respuestas de encuestas'

    def __str__(self):
        """Identifica la encuesta y el egresado."""

        return f'{self.encuesta} · {self.egresado}'


class DetalleRespuesta(models.Model):
    """Respuesta a una pregunta de una encuesta."""

    respuesta = models.ForeignKey(
        RespuestaEncuesta,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.PROTECT,
        related_name='respuestas',
    )
    valor = models.JSONField()

    class Meta:
        """Conserva una sola respuesta por pregunta."""

        constraints = [
            models.UniqueConstraint(
                fields=['respuesta', 'pregunta'],
                name='unique_answer_per_question',
            ),
        ]
        verbose_name = 'detalle de respuesta'
        verbose_name_plural = 'detalles de respuesta'

    def __str__(self):
        """Devuelve el texto de la pregunta respondida."""

        return self.pregunta.texto
