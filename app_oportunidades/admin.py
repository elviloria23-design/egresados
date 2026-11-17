"""Configuración de ofertas en el administrador de Django."""

from django.contrib import admin

from app_auditoria.services import registrar_evento

from .models import Oportunidad


@admin.register(Oportunidad)
class OportunidadAdmin(admin.ModelAdmin):
    """Permite mantener y filtrar oportunidades."""

    list_display = ('titulo', 'tipo', 'fuente', 'vigente_hasta', 'publicada')
    list_filter = ('tipo', 'publicada', 'vigente_hasta')
    search_fields = ('titulo', 'descripcion', 'fuente')
    readonly_fields = ('creada_en',)

    def save_model(self, request, obj, form, change):
        """Audita altas y actualizaciones desde Django Admin."""

        anterior = None
        if change:
            previo = Oportunidad.objects.get(pk=obj.pk)
            anterior = {
                'titulo': previo.titulo,
                'tipo': previo.tipo,
                'fuente': previo.fuente,
                'vigente_hasta': previo.vigente_hasta.isoformat(),
                'publicada': previo.publicada,
            }
        super().save_model(request, obj, form, change)
        nuevo = {
            'titulo': obj.titulo,
            'tipo': obj.tipo,
            'fuente': obj.fuente,
            'vigente_hasta': obj.vigente_hasta.isoformat(),
            'publicada': obj.publicada,
        }
        registrar_evento(
            request,
            'PUBLICAR' if not change else 'ACTUALIZAR',
            'Oportunidad',
            obj.pk,
            {'anterior': anterior, 'nuevo': nuevo},
        )

    def has_delete_permission(self, request, obj=None):
        """Conserva las oportunidades para trazabilidad."""

        return False
