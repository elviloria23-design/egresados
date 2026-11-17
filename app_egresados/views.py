"""Vistas de administración y seguimiento del padrón de egresados."""

import csv
import io
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app_auditoria.services import registrar_evento
from app_dashboard.access import ADMIN_ROLES, STAFF_ROLES, roles_required

from .forms import (
    AutogestionEgresadoForm,
    CargaMasivaForm,
    CambioEstadoForm,
    EgresadoForm,
    IntentoContactoForm,
    MotivoForm,
)
from .models import (
    ActualizacionPendiente,
    AlcanceFuncionario,
    Egresado,
    HistorialConsentimiento,
    HistorialEstado,
    HistorialDatos,
    IntentoContacto,
    ProgramaFormacion,
)

ENCABEZADOS_CSV = (
    'documento',
    'nombres',
    'apellidos',
    'correo',
    'telefono',
    'municipio',
    'programa',
    'fecha_grado',
    'elegibilidad_verificada',
    'consentimiento',
    'consentimiento_sensible',
)
VALORES_VERDADEROS = {'1', 'true', 'sí', 'si', 'yes', 'on'}


def egresados_accesibles(usuario):
    """Obtiene el padrón completo o el alcance explícito del funcionario."""

    egresados = Egresado.objects.filter(activo=True).select_related('programa')
    if usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists():
        return egresados
    if usuario.groups.filter(name='Funcionario').exists():
        try:
            alcance = usuario.alcance_funcionario
        except AlcanceFuncionario.DoesNotExist:
            return egresados.none()
        return egresados.filter(programa__in=alcance.programas.all())
    return egresados.none()


def programas_accesibles(usuario):
    """Devuelve los programas habilitados para el usuario operativo."""

    programas = ProgramaFormacion.objects.filter(activo=True)
    if usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists():
        return programas
    try:
        return usuario.alcance_funcionario.programas.filter(activo=True)
    except AlcanceFuncionario.DoesNotExist:
        return programas.none()


def _cargar_egresado_fila(request, fila, programas):
    """Valida y crea un egresado desde una fila importada."""

    errores = []
    nombre_programa = fila.get('programa', '').strip()
    programa = programas.filter(nombre__iexact=nombre_programa).first()
    if programa is None:
        programa = programas.filter(codigo__iexact=nombre_programa).first()
    if programa is None:
        errores.append(
            'El programa no coincide con un nombre o código autorizado.',
        )
        return None, errores

    data = {
        campo: fila.get(campo, '').strip()
        for campo in ENCABEZADOS_CSV
        if campo not in (
            'programa',
            'elegibilidad_verificada',
            'consentimiento',
            'consentimiento_sensible',
        )
    }
    data.update({
        'programa': str(programa.pk),
        'elegibilidad_verificada': (
            'on'
            if fila.get('elegibilidad_verificada', '').strip().lower()
            in VALORES_VERDADEROS
            else ''
        ),
        'consentimiento': (
            'on'
            if fila.get('consentimiento', '').strip().lower()
            in VALORES_VERDADEROS
            else ''
        ),
        'consentimiento_sensible': (
            'on'
            if fila.get('consentimiento_sensible', '').strip().lower()
            in VALORES_VERDADEROS
            else ''
        ),
    })
    form = EgresadoForm(data, programas=programas)
    if not form.is_valid():
        return None, [
            f'{campo}: {", ".join(str(error) for error in errores_campo)}'
            for campo, errores_campo in form.errors.items()
        ]
    if not form.cleaned_data['elegibilidad_verificada']:
        return None, ['La elegibilidad de formación titulada no está verificada.']
    if not form.cleaned_data['consentimiento']:
        return None, ['El consentimiento es obligatorio para el registro.']

    with transaction.atomic():
        egresado = form.save()
        HistorialEstado.objects.create(
            egresado=egresado,
            estado_nuevo=egresado.estado,
            justificacion='Estado inicial al importar el registro.',
            usuario=request.user,
        )
        HistorialConsentimiento.objects.create(
            egresado=egresado,
            autorizado=egresado.consentimiento,
            datos_sensibles=egresado.consentimiento_sensible,
            origen='CARGA_MASIVA',
            usuario=request.user,
        )
    return egresado, []


@roles_required(*STAFF_ROLES)
def egresados_import_template_view(request):
    """Descarga encabezados y una fila de ejemplo sin datos personales reales."""

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        'attachment; filename="plantilla-egresados.csv"'
    )
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(ENCABEZADOS_CSV)
    writer.writerow([
        '123456789',
        'Nombre de ejemplo',
        'Apellido de ejemplo',
        'ejemplo@correo.co',
        '3000000000',
        'Riohacha',
        'Codigo o nombre del programa',
        '2025-12-31',
        'si',
        'si',
        'no',
    ])
    return response


@roles_required(*STAFF_ROLES)
def egresados_import_view(request):
    """Procesa un CSV con validación independiente y resultado por fila."""

    form = CargaMasivaForm(request.POST or None, request.FILES or None)
    resultado = None
    if request.method == 'POST' and form.is_valid():
        try:
            contenido = form.cleaned_data['archivo'].read().decode('utf-8-sig')
        except UnicodeDecodeError:
            form.add_error(
                'archivo',
                'El CSV debe estar codificado en UTF-8.',
            )
            return render(
                request,
                'app_egresados/app_egresados_import.html',
                {'form': form},
            )
        lector = csv.DictReader(io.StringIO(contenido, newline=''))
        encabezados = lector.fieldnames or []
        encabezados_normalizados = [
            encabezado.strip().lower() for encabezado in encabezados
        ]
        faltantes = set(ENCABEZADOS_CSV) - set(encabezados_normalizados)
        if faltantes:
            form.add_error(
                'archivo',
                'Faltan columnas requeridas: '
                + ', '.join(sorted(faltantes)),
            )
        elif len(set(encabezados_normalizados)) != len(
            encabezados_normalizados,
        ):
            form.add_error(
                'archivo',
                'El archivo contiene nombres de columna duplicados.',
            )
        else:
            filas = []
            duplicados_archivo = set()
            errores = []
            for numero_fila, valores in enumerate(lector, start=2):
                if numero_fila > 5001:
                    errores.append({
                        'fila': numero_fila,
                        'documento': '',
                        'errores': ['El archivo supera el límite de 5.000 filas.'],
                    })
                    break
                if None in valores:
                    errores.append({
                        'fila': numero_fila,
                        'documento': valores.get('documento', ''),
                        'errores': [
                            'La fila contiene más valores que columnas.',
                        ],
                    })
                    continue
                fila = {
                    nombre.strip().lower(): valor or ''
                    for nombre, valor in valores.items()
                    if nombre is not None
                }
                documento = fila.get('documento', '').strip().replace(' ', '').upper()
                if documento and documento in duplicados_archivo:
                    errores.append({
                        'fila': numero_fila,
                        'documento': documento,
                        'errores': ['El documento está duplicado en el archivo.'],
                    })
                    continue
                if documento:
                    duplicados_archivo.add(documento)
                filas.append((numero_fila, documento, fila))
            creados = 0
            programas = programas_accesibles(request.user)
            for numero_fila, documento, fila in filas:
                try:
                    egresado, errores_fila = _cargar_egresado_fila(
                        request,
                        fila,
                        programas,
                    )
                except IntegrityError:
                    egresado = None
                    errores_fila = [
                        'Ya existe un egresado activo con este documento.',
                    ]
                if errores_fila:
                    errores.append({
                        'fila': numero_fila,
                        'documento': documento,
                        'errores': errores_fila,
                    })
                    continue
                creados += 1
                registrar_evento(
                    request,
                    'CREAR_CARGA_MASIVA',
                    'Egresado',
                    egresado.pk,
                    {
                        'documento': egresado.documento,
                        'nombre': egresado.nombre_completo,
                    },
                )
            resultado = {'creados': creados, 'errores': errores}
            registrar_evento(
                request,
                'CARGAR_CSV',
                'Egresado',
                valores={
                    'creados': creados,
                    'rechazados': len(errores),
                },
            )
            if creados:
                messages.success(
                    request,
                    f'Se importaron {creados} egresados correctamente.',
                )
            if errores:
                messages.warning(
                    request,
                    f'{len(errores)} filas requieren revisión.',
                )
    return render(
        request,
        'app_egresados/app_egresados_import.html',
        {'form': form, 'resultado': resultado},
    )


@roles_required(*STAFF_ROLES)
def egresados_list_view(request):
    """Busca y pagina el padrón dentro del alcance del usuario."""

    incluir_inactivos = (
        request.GET.get('inactivos') == '1'
        and (
            request.user.is_superuser
            or request.user.groups.filter(name__in=ADMIN_ROLES).exists()
        )
    )
    registrar_evento(
        request,
        'CONSULTAR_PADRON',
        'Egresado',
        valores={'incluir_inactivos': incluir_inactivos},
    )
    egresados = (
        Egresado.objects.filter(activo=False).select_related('programa')
        if incluir_inactivos
        else egresados_accesibles(request.user)
    )
    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    programa_id = request.GET.get('programa', '').strip()
    if query:
        egresados = egresados.filter(
            Q(documento__icontains=query)
            | Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
        )
    if estado in Egresado.Estado.values:
        egresados = egresados.filter(estado=estado)
    if programa_id.isdigit():
        egresados = egresados.filter(programa_id=programa_id)
    return render(
        request,
        'app_egresados/app_egresados_list.html',
        {
            'egresados': egresados,
            'query': query,
            'estado_seleccionado': estado,
            'programa_seleccionado': programa_id,
            'programas': programas_accesibles(request.user),
            'estados': Egresado.Estado.choices,
            'incluir_inactivos': incluir_inactivos,
        },
    )


@roles_required(*STAFF_ROLES)
def egresados_create_view(request):
    """Registra egresados elegibles con consentimiento y auditoría."""

    programas = programas_accesibles(request.user)
    form = EgresadoForm(
        request.POST or None,
        programas=programas,
    )
    if request.method == 'POST' and form.is_valid():
        if not form.cleaned_data['elegibilidad_verificada']:
            form.add_error(
                'elegibilidad_verificada',
                'La elegibilidad debe verificarse antes del registro.',
            )
        else:
            try:
                with transaction.atomic():
                    egresado = form.save()
                    HistorialEstado.objects.create(
                        egresado=egresado,
                        estado_nuevo=egresado.estado,
                        justificacion=(
                            'Estado inicial al registrar el egresado.'
                        ),
                        usuario=request.user,
                    )
                    HistorialConsentimiento.objects.create(
                        egresado=egresado,
                        autorizado=egresado.consentimiento,
                        datos_sensibles=egresado.consentimiento_sensible,
                        origen='REGISTRO',
                        usuario=request.user,
                    )
                    registrar_evento(
                        request,
                        'CREAR',
                        'Egresado',
                        egresado.pk,
                        {
                            'documento': egresado.documento,
                            'nombre': egresado.nombre_completo,
                            'programa': egresado.programa.nombre,
                            'consentimiento': egresado.consentimiento,
                        },
                    )
                messages.success(
                    request,
                    'El egresado fue registrado correctamente.',
                )
                return redirect('egresados_detail', pk=egresado.pk)
            except IntegrityError:
                form.add_error(
                    'documento',
                    'Ya existe un registro con este documento.',
                )
    return render(
        request,
        'app_egresados/app_egresados_form.html',
        {'form': form, 'titulo': 'Registrar egresado'},
    )


@roles_required(*STAFF_ROLES)
def egresados_detail_view(request, pk):
    """Muestra la ficha e historial dentro del alcance asignado."""

    egresado = get_object_or_404(egresados_accesibles(request.user), pk=pk)
    registrar_evento(
        request,
        'CONSULTAR_FICHA',
        'Egresado',
        egresado.pk,
    )
    return render(
        request,
        'app_egresados/app_egresados_detail.html',
        {
            'egresado': egresado,
            'historial': egresado.historial_estados.select_related('usuario'),
            'intentos': (
                egresado.intentos_contacto.select_related('usuario')[:8]
            ),
            'form_contacto': IntentoContactoForm(),
            'form_estado': CambioEstadoForm(
                initial={'estado': egresado.estado},
            ),
            'puede_baja': (
                request.user.is_superuser
                or request.user.groups.filter(name__in=ADMIN_ROLES).exists()
            ),
        },
    )


@roles_required(*STAFF_ROLES)
def egresados_update_view(request, pk):
    """Actualiza datos de contacto y registra el cambio en auditoría."""

    egresado = get_object_or_404(egresados_accesibles(request.user), pk=pk)
    programas = programas_accesibles(request.user)
    form = EgresadoForm(
        request.POST or None,
        instance=egresado,
        programas=programas,
    )
    if request.method == 'POST' and form.is_valid():
        anterior = {
            'correo': egresado.correo,
            'telefono': egresado.telefono,
            'municipio': egresado.municipio,
            'programa': egresado.programa_id,
            'fecha_grado': egresado.fecha_grado.isoformat(),
            'consentimiento': egresado.consentimiento,
            'consentimiento_sensible': egresado.consentimiento_sensible,
            'estado': egresado.estado,
        }
        actualizado = form.save(commit=False)
        actualizado.ultima_actualizacion = timezone.localdate()
        actualizado.save()
        nuevo = {
            'correo': actualizado.correo,
            'telefono': actualizado.telefono,
            'municipio': actualizado.municipio,
            'programa': actualizado.programa_id,
            'fecha_grado': actualizado.fecha_grado.isoformat(),
            'consentimiento': actualizado.consentimiento,
            'consentimiento_sensible': actualizado.consentimiento_sensible,
            'estado': actualizado.estado,
        }
        HistorialDatos.objects.create(
            egresado=actualizado,
            valores={'anterior': anterior, 'nuevo': nuevo},
            origen='FUNCIONARIO',
            usuario=request.user,
        )
        if (
            anterior['consentimiento'] != actualizado.consentimiento
            or anterior['consentimiento_sensible']
            != actualizado.consentimiento_sensible
        ):
            HistorialConsentimiento.objects.create(
                egresado=actualizado,
                autorizado=actualizado.consentimiento,
                datos_sensibles=actualizado.consentimiento_sensible,
                origen='FUNCIONARIO',
                usuario=request.user,
            )
        registrar_evento(
            request,
            'ACTUALIZAR',
            'Egresado',
            egresado.pk,
            {
                'anterior': anterior,
                'nuevo': nuevo,
            },
        )
        messages.success(request, 'La ficha se actualizó correctamente.')
        return redirect('egresados_detail', pk=egresado.pk)
    return render(
        request,
        'app_egresados/app_egresados_form.html',
        {'form': form, 'titulo': 'Actualizar ficha'},
    )


@roles_required(*STAFF_ROLES)
def egresados_contacto_create_view(request, pk):
    """Guarda un intento de contacto y aplica la regla de inactividad."""

    if request.method != 'POST':
        raise PermissionDenied
    egresado = get_object_or_404(egresados_accesibles(request.user), pk=pk)
    form = IntentoContactoForm(request.POST)
    if form.is_valid():
        intento = form.save(commit=False)
        intento.egresado = egresado
        intento.usuario = request.user
        intento.save()
        if intento.resultado == IntentoContacto.Resultado.CONTACTADO:
            egresado.ultima_actualizacion = timezone.localdate()
            egresado.save(
                update_fields=['ultima_actualizacion', 'actualizado_en'],
            )
        registrar_evento(
            request,
            'REGISTRAR_CONTACTO',
            'Egresado',
            egresado.pk,
            {'resultado': intento.resultado, 'medio': intento.medio},
        )
        intentos_fallidos = egresado.intentos_contacto.filter(
            resultado__in=(
                IntentoContacto.Resultado.SIN_RESPUESTA,
                IntentoContacto.Resultado.DATOS_INVALIDOS,
            ),
            fecha__gte=timezone.localdate() - timedelta(days=60),
        ).count()
        if (
            intentos_fallidos >= 2
            and egresado.estado != Egresado.Estado.INACTIVO
        ):
            _cambiar_estado(
                request,
                egresado,
                Egresado.Estado.INACTIVO,
                'Dos intentos fallidos de contacto dentro de 60 días.',
            )
        messages.success(request, 'El intento de contacto quedó registrado.')
    else:
        messages.error(request, 'Revisa los datos del intento de contacto.')
    return redirect('egresados_detail', pk=egresado.pk)


def _cambiar_estado(request, egresado, estado_nuevo, justificacion):
    """Actualiza el estado creando historial y auditoría en una transacción."""

    estado_anterior = egresado.estado
    if estado_anterior == estado_nuevo:
        return
    with transaction.atomic():
        egresado.estado = estado_nuevo
        egresado.ultima_actualizacion = timezone.localdate()
        egresado.save(
            update_fields=['estado', 'ultima_actualizacion', 'actualizado_en'],
        )
        HistorialEstado.objects.create(
            egresado=egresado,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            justificacion=justificacion,
            usuario=request.user,
        )
        registrar_evento(
            request,
            'CAMBIAR_ESTADO',
            'Egresado',
            egresado.pk,
            {
                'anterior': estado_anterior,
                'nuevo': estado_nuevo,
                'justificacion': justificacion,
            },
        )


@roles_required(*STAFF_ROLES)
def egresados_estado_view(request, pk):
    """Cambia el estado únicamente con justificación documentada."""

    if request.method != 'POST':
        raise PermissionDenied
    egresado = get_object_or_404(egresados_accesibles(request.user), pk=pk)
    form = CambioEstadoForm(request.POST)
    if form.is_valid():
        _cambiar_estado(
            request,
            egresado,
            form.cleaned_data['estado'],
            form.cleaned_data['justificacion'],
        )
        messages.success(request, 'El estado del egresado fue actualizado.')
    else:
        messages.error(request, 'Indica un estado válido y una justificación.')
    return redirect('egresados_detail', pk=egresado.pk)


@roles_required(*ADMIN_ROLES)
def egresados_baja_view(request, pk):
    """Aplica baja lógica sin eliminar físicamente información personal."""

    if request.method != 'POST':
        raise PermissionDenied
    egresado = get_object_or_404(Egresado, pk=pk)
    form = MotivoForm(request.POST)
    if form.is_valid():
        egresado.activo = False
        egresado.save(update_fields=['activo', 'actualizado_en'])
        registrar_evento(
            request,
            'BAJA_LOGICA',
            'Egresado',
            egresado.pk,
            {
                'anterior': {'activo': True},
                'nuevo': {'activo': False},
                'motivo': form.cleaned_data['motivo'],
            },
        )
        messages.success(request, 'El registro fue dado de baja lógicamente.')
        return redirect('egresados_list')
    messages.error(request, 'Es necesario indicar el motivo de la baja.')
    return redirect('egresados_detail', pk=egresado.pk)


@roles_required(*ADMIN_ROLES)
def egresados_restore_view(request, pk):
    """Restaura un registro dado de baja con traza del administrador."""

    if request.method != 'POST':
        raise PermissionDenied
    egresado = get_object_or_404(Egresado, pk=pk, activo=False)
    egresado.activo = True
    egresado.save(update_fields=['activo', 'actualizado_en'])
    registrar_evento(
        request,
        'RESTAURAR',
        'Egresado',
        egresado.pk,
        {'anterior': {'activo': False}, 'nuevo': {'activo': True}},
    )
    messages.success(request, 'El registro fue restaurado.')
    return redirect('egresados_list')


@roles_required(*STAFF_ROLES)
def egresados_pendientes_view(request):
    """Presenta solicitudes de actualización para revisión institucional."""

    pendientes = ActualizacionPendiente.objects.filter(
        verificada=False,
        egresado__in=egresados_accesibles(request.user),
    ).select_related('egresado', 'egresado__programa')
    return render(
        request,
        'app_egresados/app_egresados_pendientes.html',
        {'pendientes': pendientes},
    )


@roles_required(*STAFF_ROLES)
def egresados_verificar_actualizacion_view(request, pk):
    """Aprueba una actualización de situación propuesta por el egresado."""

    if request.method != 'POST':
        raise PermissionDenied
    actualizacion = get_object_or_404(
        ActualizacionPendiente.objects.select_related('egresado'),
        pk=pk,
        verificada=False,
        egresado__in=egresados_accesibles(request.user),
    )
    estado = actualizacion.valores.get('estado')
    if estado not in Egresado.Estado.values:
        messages.error(request, 'La solicitud no contiene un estado válido.')
        return redirect('egresados_pendientes')
    _cambiar_estado(
        request,
        actualizacion.egresado,
        estado,
        'Situación reportada por el egresado y verificada por un funcionario.',
    )
    actualizacion.verificada = True
    actualizacion.verificada_por = request.user
    actualizacion.verificada_en = timezone.now()
    actualizacion.save(
        update_fields=['verificada', 'verificada_por', 'verificada_en']
    )
    registrar_evento(
        request,
        'VERIFICAR_ACTUALIZACION',
        'ActualizacionPendiente',
        actualizacion.pk,
    )
    messages.success(request, 'La actualización quedó verificada.')
    return redirect('egresados_pendientes')


@login_required
def egresados_self_update_view(request):
    """Actualiza los datos propios y envía la situación a verificación."""

    if not request.user.groups.filter(name='Egresado').exists():
        raise PermissionDenied
    try:
        egresado = request.user.ficha_egresado
    except Egresado.DoesNotExist as error:
        raise PermissionDenied from error

    form = AutogestionEgresadoForm(
        request.POST or None,
        initial={
            'correo': egresado.correo,
            'telefono': egresado.telefono,
            'municipio': egresado.municipio,
            'estado': egresado.estado,
            'consentimiento': egresado.consentimiento,
            'consentimiento_sensible': egresado.consentimiento_sensible,
        },
    )
    if request.method == 'POST' and form.is_valid():
        anterior = {
            'correo': egresado.correo,
            'telefono': egresado.telefono,
            'municipio': egresado.municipio,
            'consentimiento': egresado.consentimiento,
            'consentimiento_sensible': egresado.consentimiento_sensible,
        }
        egresado.correo = form.cleaned_data['correo']
        egresado.telefono = form.cleaned_data['telefono']
        egresado.municipio = form.cleaned_data['municipio']
        egresado.consentimiento = form.cleaned_data['consentimiento']
        egresado.consentimiento_sensible = (
            form.cleaned_data['consentimiento_sensible']
        )
        if egresado.consentimiento:
            if not egresado.consentimiento_fecha:
                egresado.consentimiento_fecha = timezone.now()
        else:
            egresado.consentimiento_fecha = None
        egresado.ultima_actualizacion = timezone.localdate()
        egresado.save(
            update_fields=[
                'correo',
                'telefono',
                'municipio',
                'consentimiento',
                'consentimiento_sensible',
                'consentimiento_fecha',
                'ultima_actualizacion',
                'actualizado_en',
            ]
        )
        ActualizacionPendiente.objects.create(
            egresado=egresado,
            valores={'estado': form.cleaned_data['estado']},
        )
        nuevo = {
            'correo': egresado.correo,
            'telefono': egresado.telefono,
            'municipio': egresado.municipio,
            'estado_reportado': form.cleaned_data['estado'],
        }
        HistorialDatos.objects.create(
            egresado=egresado,
            valores={'anterior': anterior, 'nuevo': nuevo},
            origen='AUTOGESTION',
            usuario=request.user,
        )
        if (
            anterior['consentimiento'] != egresado.consentimiento
            or anterior['consentimiento_sensible']
            != egresado.consentimiento_sensible
        ):
            HistorialConsentimiento.objects.create(
                egresado=egresado,
                autorizado=egresado.consentimiento,
                datos_sensibles=egresado.consentimiento_sensible,
                origen='AUTOGESTION',
                usuario=request.user,
            )
        registrar_evento(
            request,
            'AUTOGESTION',
            'Egresado',
            egresado.pk,
            {
                'anterior': anterior,
                'nuevo': nuevo,
            },
        )
        messages.success(
            request,
            'Tus datos de contacto están actualizados. La situación reportada '
            'quedó pendiente de verificación.',
        )
        return redirect('dashboard')
    return render(
        request,
        'app_egresados/app_egresados_self_update.html',
        {'form': form},
    )
