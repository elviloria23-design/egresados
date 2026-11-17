"""Configuración de consulta de la bitácora en Django admin."""

from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Expone auditoría en modo de solo lectura."""

    list_display = (
        'accion',
        'entidad',
        'usuario',
        'direccion_ip',
        'creado_en',
    )
    list_filter = ('accion', 'entidad', 'creado_en')
    search_fields = ('entidad_id', 'usuario__username', 'accion')
    readonly_fields = (
        'usuario',
        'accion',
        'entidad',
        'entidad_id',
        'valores',
        'direccion_ip',
        'creado_en',
    )

    def has_add_permission(self, request):
        """Impide crear eventos manualmente."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar eventos existentes."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impide borrar la bitácora."""

        return False
