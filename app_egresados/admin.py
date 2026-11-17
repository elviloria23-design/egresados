"""Configuración del padrón en el administrador de Django."""

from django.contrib import admin

from app_auditoria.services import registrar_evento

from .models import (
    AlcanceFuncionario,
    ActualizacionPendiente,
    Egresado,
    HistorialConsentimiento,
    HistorialDatos,
    HistorialEstado,
    IntentoContacto,
    ProgramaFormacion,
)


@admin.register(AlcanceFuncionario)
class AlcanceFuncionarioAdmin(admin.ModelAdmin):
    """Administra el alcance por programa de los funcionarios."""

    list_display = ('usuario',)
    filter_horizontal = ('programas',)
    search_fields = ('usuario__username', 'usuario__email')


@admin.register(ProgramaFormacion)
class ProgramaFormacionAdmin(admin.ModelAdmin):
    """Permite mantener el catálogo de programas."""

    list_display = ('nombre', 'codigo', 'activo')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo',)


class HistorialEstadoInline(admin.TabularInline):
    """Muestra el historial de estados dentro del egresado."""

    model = HistorialEstado
    can_delete = False
    extra = 0
    show_change_link = False
    readonly_fields = (
        'estado_anterior',
        'estado_nuevo',
        'justificacion',
        'usuario',
        'creado_en',
    )

    def has_add_permission(self, request, obj=None):
        """Impide alterar el historial desde el administrador."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar cambios de estado."""

        return False


@admin.register(Egresado)
class EgresadoAdmin(admin.ModelAdmin):
    """Expone el padrón con búsqueda y filtros."""

    list_display = (
        'documento',
        'nombre_completo',
        'programa',
        'estado',
        'municipio',
        'activo',
    )
    list_filter = ('estado', 'programa', 'municipio', 'activo')
    search_fields = ('documento', 'nombres', 'apellidos', 'correo')
    readonly_fields = ('creado_en', 'actualizado_en', 'estado', 'activo')
    inlines = [HistorialEstadoInline]

    def save_model(self, request, obj, form, change):
        """Audita los cambios y registra consentimientos modificados."""

        anterior = None
        if change:
            previo = Egresado.objects.get(pk=obj.pk)
            anterior = {
                'correo': previo.correo,
                'telefono': previo.telefono,
                'municipio': previo.municipio,
                'programa': previo.programa_id,
                'consentimiento': previo.consentimiento,
                'consentimiento_sensible': previo.consentimiento_sensible,
            }
        super().save_model(request, obj, form, change)
        nuevo = {
            'correo': obj.correo,
            'telefono': obj.telefono,
            'municipio': obj.municipio,
            'programa': obj.programa_id,
            'consentimiento': obj.consentimiento,
            'consentimiento_sensible': obj.consentimiento_sensible,
        }
        if not change:
            HistorialEstado.objects.create(
                egresado=obj,
                estado_nuevo=obj.estado,
                justificacion='Estado inicial al registrar el egresado.',
                usuario=request.user,
            )
            HistorialConsentimiento.objects.create(
                egresado=obj,
                autorizado=obj.consentimiento,
                datos_sensibles=obj.consentimiento_sensible,
                origen='REGISTRO',
                usuario=request.user,
            )
        else:
            HistorialDatos.objects.create(
                egresado=obj,
                valores={'anterior': anterior, 'nuevo': nuevo},
                origen='FUNCIONARIO',
                usuario=request.user,
            )
            if (
                anterior['consentimiento'] != obj.consentimiento
                or anterior['consentimiento_sensible']
                != obj.consentimiento_sensible
            ):
                HistorialConsentimiento.objects.create(
                    egresado=obj,
                    autorizado=obj.consentimiento,
                    datos_sensibles=obj.consentimiento_sensible,
                    origen='FUNCIONARIO',
                    usuario=request.user,
                )
        registrar_evento(
            request,
            'CREAR' if not change else 'ACTUALIZAR',
            'Egresado',
            obj.pk,
            {'anterior': anterior, 'nuevo': nuevo},
        )

    def has_delete_permission(self, request, obj=None):
        """Impide la eliminación física de registros de egresados."""

        return False

@admin.register(IntentoContacto)
class IntentoContactoAdmin(admin.ModelAdmin):
    """Permite consultar intentos de seguimiento."""

    list_display = ('egresado', 'fecha', 'medio', 'resultado', 'usuario')
    list_filter = ('resultado', 'medio', 'fecha')
    search_fields = ('egresado__documento', 'egresado__nombres')
    readonly_fields = ('creado_en',)


@admin.register(ActualizacionPendiente)
class ActualizacionPendienteAdmin(admin.ModelAdmin):
    """Permite revisar las solicitudes de autogestión."""

    list_display = ('egresado', 'origen', 'verificada', 'creado_en')
    list_filter = ('verificada', 'origen')
    search_fields = ('egresado__documento', 'egresado__nombres')
    readonly_fields = ('creado_en', 'verificada_en')


@admin.register(HistorialDatos)
class HistorialDatosAdmin(admin.ModelAdmin):
    """Expone las versiones de información en modo de solo lectura."""

    list_display = ('egresado', 'origen', 'usuario', 'creado_en')
    list_filter = ('origen', 'creado_en')
    search_fields = ('egresado__documento', 'egresado__nombres')
    readonly_fields = ('egresado', 'valores', 'origen', 'usuario', 'creado_en')

    def has_add_permission(self, request):
        """Impide crear versiones manualmente."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide editar el historial de versiones."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impide eliminar versiones de datos."""

        return False


@admin.register(HistorialConsentimiento)
class HistorialConsentimientoAdmin(admin.ModelAdmin):
    """Expone consentimientos y revocaciones en modo de solo lectura."""

    list_display = (
        'egresado',
        'autorizado',
        'datos_sensibles',
        'origen',
        'usuario',
        'creado_en',
    )
    list_filter = ('autorizado', 'datos_sensibles', 'origen', 'creado_en')
    search_fields = ('egresado__documento', 'egresado__nombres')
    readonly_fields = (
        'egresado',
        'autorizado',
        'datos_sensibles',
        'version_politica',
        'origen',
        'usuario',
        'creado_en',
    )

    def has_add_permission(self, request):
        """Impide crear autorizaciones manualmente."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar el historial de autorizaciones."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impide eliminar registros de consentimiento."""

        return False
