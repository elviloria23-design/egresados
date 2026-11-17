"""Configuración de administración de certificaciones."""

from django.contrib import admin

from .models import Certificacion


@admin.register(Certificacion)
class CertificacionAdmin(admin.ModelAdmin):
    """Permite consultar certificados y gestionar su estado."""

    list_display = (
        'numero',
        'tipo',
        'egresado',
        'estado',
        'emitida_por',
        'emitida_en',
    )
    list_filter = ('estado', 'emitida_en')
    search_fields = (
        'numero',
        'codigo_verificacion',
        'egresado__documento',
        'egresado__nombres',
    )
    readonly_fields = (
        'numero',
        'codigo_verificacion',
        'egresado',
        'tipo',
        'motivo',
        'estado',
        'emitida_por',
        'emitida_en',
        'anulada_por',
        'anulacion_motivo',
        'anulada_en',
    )

    def has_add_permission(self, request):
        """Impide emitir certificados sin ejecutar los controles funcionales."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar certificados desde el administrador."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impide eliminar documentos institucionales."""

        return False
