"""Configuración de administración de encuestas y respuestas."""

from django.contrib import admin

from .models import (
    DetalleRespuesta,
    Encuesta,
    Pregunta,
    RespuestaEncuesta,
)


class PreguntaInline(admin.TabularInline):
    """Permite editar preguntas dentro de la encuesta."""

    model = Pregunta
    extra = 0


@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    """Administra encuestas, vigencia y programas destinatarios."""

    list_display = ('titulo', 'publicada', 'inicia_en', 'finaliza_en', 'creada_por')
    list_filter = ('publicada', 'inicia_en', 'finaliza_en', 'programas')
    search_fields = ('titulo', 'descripcion')
    filter_horizontal = ('programas',)
    inlines = [PreguntaInline]


class DetalleRespuestaInline(admin.TabularInline):
    """Presenta respuestas por pregunta en modo de solo lectura."""

    model = DetalleRespuesta
    extra = 0
    can_delete = False
    readonly_fields = ('pregunta', 'valor')

    def has_add_permission(self, request, obj=None):
        """Impide agregar respuestas manualmente."""

        return False


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    """Permite auditar las respuestas de los participantes."""

    list_display = ('encuesta', 'egresado', 'respondida_en')
    list_filter = ('encuesta', 'respondida_en')
    search_fields = ('encuesta__titulo', 'egresado__documento')
    readonly_fields = ('encuesta', 'egresado', 'respondida_en')
    inlines = [DetalleRespuestaInline]

    def has_add_permission(self, request):
        """Impide crear respuestas desde el administrador."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar respuestas."""

        return False
