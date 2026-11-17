"""Vistas para indicadores agregados y exportación con control de acceso."""

import csv
from datetime import date, timedelta

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from app_auditoria.services import registrar_evento
from app_dashboard.access import ADMIN_ROLES, VIEWER_ROLES, roles_required
from app_egresados.models import (
    AlcanceFuncionario,
    Egresado,
    ProgramaFormacion,
)


def _alcance_reportes(usuario):
    """Limita indicadores al programa asignado a cada funcionario o visor."""

    egresados = Egresado.objects.filter(activo=True).select_related('programa')
    if usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists():
        return egresados
    try:
        programas = usuario.alcance_funcionario.programas.all()
    except AlcanceFuncionario.DoesNotExist:
        return egresados.none()
    return egresados.filter(programa__in=programas)


def _solo_agregados(usuario):
    """Indica si el usuario debe recibir exclusivamente información agregada."""

    return not (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=ADMIN_ROLES + ('Funcionario',),
        ).exists()
    )


def _filtrar_periodo(request, egresados):
    """Aplica filtros validados de año y programa al reporte."""

    anio = request.GET.get('anio', '').strip()
    programa_id = request.GET.get('programa', '').strip()
    if anio.isdigit() and 1900 <= int(anio) <= date.today().year + 1:
        egresados = egresados.filter(fecha_grado__year=int(anio))
    else:
        anio = ''
    if programa_id.isdigit():
        egresados = egresados.filter(programa_id=int(programa_id))
    else:
        programa_id = ''
    return egresados, anio, programa_id


@roles_required(*VIEWER_ROLES)
def reportes_dashboard_view(request):
    """Presenta indicadores agregados según los permisos del usuario."""

    egresados = _alcance_reportes(request.user)
    egresados, anio, programa_id = _filtrar_periodo(request, egresados)
    total = egresados.count()
    por_estado = [
        {
            'nombre': nombre,
            'cantidad': egresados.filter(estado=estado).count(),
        }
        for estado, nombre in Egresado.Estado.choices
    ]
    por_programa = [
        {
            'nombre': fila['programa__nombre'],
            'cantidad': fila['total'],
        }
        for fila in egresados.values('programa__nombre').order_by(
            'programa__nombre',
        ).annotate(total=Count('pk'))
    ]
    actualizados = egresados.filter(
        ultima_actualizacion__gte=timezone.localdate() - timedelta(days=365),
    ).count()
    alcance = _alcance_reportes(request.user)
    return render(
        request,
        'app_reportes/app_reportes_dashboard.html',
        {
            'total': total,
            'por_estado': por_estado,
            'por_programa': por_programa,
            'programas': ProgramaFormacion.objects.filter(
                pk__in=alcance.values('programa_id'),
            ),
            'anio': anio,
            'programa_seleccionado': programa_id,
            'solo_agregados': _solo_agregados(request.user),
            'cobertura': round(actualizados * 100 / total) if total else 0,
            'actualizados': actualizados,
        },
    )


def _proteger_formula(valor):
    """Neutraliza valores que una hoja de cálculo podría ejecutar como fórmula."""

    texto = str(valor or '')
    if texto.lstrip().startswith(('=', '+', '-', '@')):
        return f"'{texto}"
    return texto


@roles_required(*VIEWER_ROLES)
def reportes_export_view(request):
    """Exporta CSV agregado para visor o detalle permitido para el equipo."""

    egresados = _alcance_reportes(request.user)
    egresados, anio, programa_id = _filtrar_periodo(request, egresados)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        'attachment; filename="reporte-egresados.csv"'
    )
    response.write('\ufeff')
    writer = csv.writer(response)
    if _solo_agregados(request.user):
        writer.writerow(['Programa', 'Estado', 'Cantidad'])
        rows = egresados.values(
            'programa__nombre',
            'estado',
        ).order_by('programa__nombre', 'estado').annotate(
            total=Count('pk'),
        )
        for row in rows:
            writer.writerow([
                _proteger_formula(row['programa__nombre']),
                _proteger_formula(row['estado']),
                row['total'],
            ])
    else:
        writer.writerow([
            'Documento',
            'Nombres',
            'Apellidos',
            'Correo',
            'Teléfono',
            'Municipio',
            'Programa',
            'Fecha de grado',
            'Estado',
            'Último seguimiento',
        ])
        for egresado in egresados.order_by('apellidos', 'nombres').iterator():
            writer.writerow([
                _proteger_formula(egresado.documento),
                _proteger_formula(egresado.nombres),
                _proteger_formula(egresado.apellidos),
                _proteger_formula(egresado.correo),
                _proteger_formula(egresado.telefono),
                _proteger_formula(egresado.municipio),
                _proteger_formula(egresado.programa.nombre),
                egresado.fecha_grado.isoformat(),
                _proteger_formula(egresado.get_estado_display()),
                egresado.ultima_actualizacion.isoformat(),
            ])
    registrar_evento(
        request,
        'EXPORTAR_REPORTE',
        'Egresado',
        valores={
            'anio': anio,
            'programa': programa_id,
            'tipo': 'AGREGADO' if _solo_agregados(request.user) else 'DETALLADO',
        },
    )
    return response
