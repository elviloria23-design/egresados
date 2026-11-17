"""Modelos centrales para el padrón y seguimiento de egresados."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProgramaFormacion(models.Model):
    """Programa de formación titulada ofrecido por el centro."""

    nombre = models.CharField(max_length=180, unique=True)
    codigo = models.CharField(max_length=40, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        """Ordena programas por nombre."""

        ordering = ['nombre']
        verbose_name = 'programa de formación'
        verbose_name_plural = 'programas de formación'

    def __str__(self):
        """Devuelve el nombre del programa."""

        return self.nombre


class AlcanceFuncionario(models.Model):
    """Asigna los programas que un funcionario puede consultar y gestionar."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alcance_funcionario',
    )
    programas = models.ManyToManyField(
        ProgramaFormacion,
        blank=True,
        related_name='funcionarios_asignados',
    )

    class Meta:
        """Identifica el alcance operativo de cada funcionario."""

        verbose_name = 'alcance de funcionario'
        verbose_name_plural = 'alcances de funcionarios'

    def __str__(self):
        """Devuelve el nombre de usuario asociado."""

        return self.usuario.get_username()


class Egresado(models.Model):
    """Ficha de contacto, formación, estado y consentimiento del egresado."""

    class Estado(models.TextChoices):
        """Estados institucionales definidos para el seguimiento."""

        ACTIVO = 'ACTIVO', 'Activo'
        VINCULADO_LABORAL = 'VINCULADO_LABORAL', 'Vinculado laboralmente'
        EMPRENDEDOR = 'EMPRENDEDOR', 'Emprendedor'
        CONTINUIDAD_FORMATIVA = (
            'CONTINUIDAD_FORMATIVA',
            'Continuidad formativa',
        )
        INACTIVO = 'INACTIVO', 'Inactivo'
        FALLECIDO = 'FALLECIDO', 'Fallecido'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ficha_egresado',
    )
    documento = models.CharField(max_length=30)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    programa = models.ForeignKey(
        ProgramaFormacion,
        on_delete=models.PROTECT,
        related_name='egresados',
    )
    fecha_grado = models.DateField()
    elegibilidad_verificada = models.BooleanField(default=False)
    consentimiento = models.BooleanField(default=False)
    consentimiento_sensible = models.BooleanField(default=False)
    consentimiento_fecha = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )
    ultima_actualizacion = models.DateField(default=timezone.localdate)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        """Prioriza los registros recientes y define búsquedas frecuentes."""

        ordering = ['apellidos', 'nombres']
        permissions = [
            (
                'gestionar_todos_egresados',
                'Puede gestionar todos los egresados',
            ),
            (
                'gestionar_egresados_area',
                'Puede gestionar egresados de su área',
            ),
        ]
        indexes = [
            models.Index(fields=['estado', 'activo']),
            models.Index(fields=['municipio', 'programa']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['documento'],
                condition=models.Q(activo=True),
                name='unique_active_alumni_document',
            ),
        ]
        verbose_name = 'egresado'
        verbose_name_plural = 'egresados'

    def __str__(self):
        """Devuelve el nombre y documento del egresado."""

        return f'{self.nombres} {self.apellidos} · {self.documento}'

    @property
    def nombre_completo(self):
        """Devuelve el nombre completo del egresado."""

        return f'{self.nombres} {self.apellidos}'.strip()


class HistorialEstado(models.Model):
    """Conserva el historial inmutable de los estados del egresado."""

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='historial_estados',
    )
    estado_anterior = models.CharField(
        max_length=30,
        choices=Egresado.Estado.choices,
        blank=True,
    )
    estado_nuevo = models.CharField(
        max_length=30,
        choices=Egresado.Estado.choices,
    )
    justificacion = models.TextField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena el historial cronológicamente."""

        ordering = ['-creado_en']
        verbose_name = 'cambio de estado'
        verbose_name_plural = 'historial de estados'

    def __str__(self):
        """Describe el cambio de estado."""

        return (
            f'{self.egresado} · {self.estado_anterior} → {self.estado_nuevo}'
        )


class IntentoContacto(models.Model):
    """Registra los intentos documentados de contacto."""

    class Resultado(models.TextChoices):
        """Resultados posibles de un intento de seguimiento."""

        CONTACTADO = 'CONTACTADO', 'Contactado'
        SIN_RESPUESTA = 'SIN_RESPUESTA', 'Sin respuesta'
        DATOS_INVALIDOS = 'DATOS_INVALIDOS', 'Datos inválidos'

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='intentos_contacto',
    )
    fecha = models.DateField(default=timezone.localdate)
    medio = models.CharField(max_length=40)
    resultado = models.CharField(max_length=24, choices=Resultado.choices)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena intentos del más reciente al más antiguo."""

        ordering = ['-fecha', '-creado_en']
        verbose_name = 'intento de contacto'
        verbose_name_plural = 'intentos de contacto'

    def __str__(self):
        """Describe el intento de contacto."""

        return (
            f'{self.egresado} · {self.fecha} · {self.get_resultado_display()}'
        )


class ActualizacionPendiente(models.Model):
    """Versiona los cambios de autogestión que esperan verificación."""

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='actualizaciones_pendientes',
    )
    valores = models.JSONField()
    origen = models.CharField(max_length=20, default='AUTOGESTION')
    verificada = models.BooleanField(default=False)
    verificada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actualizaciones_verificadas',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    verificada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Presenta primero las actualizaciones aún pendientes."""

        ordering = ['verificada', '-creado_en']
        verbose_name = 'actualización pendiente'
        verbose_name_plural = 'actualizaciones pendientes'

    def __str__(self):
        """Resume la solicitud de actualización."""

        return f'Actualización de {self.egresado} · {self.creado_en:%Y-%m-%d}'


class HistorialDatos(models.Model):
    """Conserva versiones anteriores y nuevas de cambios de la ficha."""

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='historial_datos',
    )
    valores = models.JSONField()
    origen = models.CharField(max_length=20)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las versiones desde la más reciente."""

        ordering = ['-creado_en']
        verbose_name = 'versión de datos'
        verbose_name_plural = 'versiones de datos'

    def __str__(self):
        """Describe el origen de la versión guardada."""

        return f'{self.egresado} · {self.origen} · {self.creado_en:%Y-%m-%d}'


class HistorialConsentimiento(models.Model):
    """Registra autorizaciones y revocaciones de tratamiento de datos."""

    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.PROTECT,
        related_name='historial_consentimientos',
    )
    autorizado = models.BooleanField()
    datos_sensibles = models.BooleanField(default=False)
    version_politica = models.CharField(max_length=20, default='1.0')
    origen = models.CharField(max_length=20)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las autorizaciones y revocaciones cronológicamente."""

        ordering = ['-creado_en']
        verbose_name = 'historial de consentimiento'
        verbose_name_plural = 'historial de consentimientos'

    def __str__(self):
        """Describe el último estado de autorización."""

        estado = 'Autorizado' if self.autorizado else 'Revocado'
        return f'{self.egresado} · {estado} · {self.creado_en:%Y-%m-%d}'
